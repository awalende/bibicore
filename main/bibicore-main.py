from novaclient import client
from time import sleep
import sys
import os
import configparser
import yaml
import random
import requests



DIR_PATH = os.path.dirname(os.path.realpath(__file__))
CLOUD_CONFIG_PATH= DIR_PATH+ "/yaml/cloud-config.yaml"
DISCOVERY_CONFIG_PATH = DIR_PATH + "/yaml/discovery.yaml"
TOKEN_TIMEOUT=10
TOKEN_SUFFIX='/v2/keys/_etcd/registry/'

'''
TODO:
Write Readme.
'''


'''
Checks if a environment variable is actually set in the operating system without
throwing any exceptions.
'''
def checkEnvironmentFromOS(key):
    return key in os.environ

'''
Check if all mandatory variables for openstack are set and findable.
If a variable is not set, the programm will exit.
Compare the example file, located at ../config/example.ini for further infos.
'''
def validateEnvironmentDict(dict, configFile):
    newDict = {}
    itemList = dict.items()
    for item in itemList:
        if item[1] == "":
            #print(item[0] + " is not set, looking for environment variable from OS.")
            if checkEnvironmentFromOS(item[0]):
                print("Found corresponding environment variable: " + item[0])
                newDict[item[0]] = os.environ[item[0]]
                continue
            else:
                #print("Looking for variable in .ini file...")
                try:
                    newDict[item[0]] = configFile['config'][item[0]]
                    print("Found variable in config file: " + item[0])
                    continue
                except KeyError:
                    print("Key named " + item[0] + " not found in OS or config file!")
                    print("Make sure all variables are set either by environment or config.ini file. Exiting.")
                    exit(-1)
        newDict[item[0]] = item[1]
    return newDict


'''
Builds and returns the essential dictionary with all important fields for openstack.
'''
def createEnvironmentDict(configFile):
    #needs to be cleaned up after debugging
    environmentDict = {}
    environmentDict['OS_USERNAME'] = ""
    environmentDict['OS_PASSWORD'] = ""
    environmentDict['OS_AUTH_URL'] = ""
    environmentDict['OS_TENANT_NAME'] = ""
    environmentDict['OS_FLAVOR'] = ""
    environmentDict['OS_SSH_NAME'] = ""
    environmentDict['FLOATING_IP_POOL'] = ""
    environmentDict = validateEnvironmentDict(environmentDict, configFile)
    return environmentDict


'''
Returns an image object if there is any CoreOS Image in the imagebrowser of openstack.
'''
def obtain_coreos_image(connection):
    imageList = connection.images.list()
    for image in imageList:
        if "CoreOS" in image.name:
            print("Found CoreOS Image: " + image.name)
            return image
    print("Could not find any CoreOS Image...exiting.")
    exit(-1)

'''
Returns a NIC Object.
'''
def obtainNIC(connection, NICName):
    nicList = connection.networks.list()
    for network in nicList:
        if network.label == NICName:
            print("Found network: " + network.label)
            return network
    print("Could not find network! Following networks are available:")
    print(nicList)
    exit(-1)

'''
Returns a flavor object, depending on the given name of the flavor.
If no matching flavor could be found, the programm will exit and print possible flavors.
'''
def obtainDesiredFlavor(connection, flavorName):
    flavorList = connection.flavors.list()
    for flavor in flavorList:
        if flavor.name == flavorName:
            print("Found desired flavor: " + flavor.name)
            return flavor
    print("Could not find flavor: "  + flavorName + "\n" "Following flavors are available:")
    print(flavorList)
    exit(-1)

'''
Returns an optional flavor for the discovery service, if needed.
Will not exit the programm if there are no flavors.
'''
def getDiscoveryFlavour(connection, configFile):
    try:
        desiredFlavor = configFile['discovery']['DISCOVERY_FLAVOR']
        flavorList = connection.flavors.list()
        for flavor in flavorList:
            if flavor.name == desiredFlavor:
                print("Found desired flavor for discovery service: " +desiredFlavor)
                return flavor
        print("Could not find flavor: " + desiredFlavor + "\n" "Following flavors are available:")
        print(flavorList)
        exit(-1)
    except KeyError:
        print("No special flavor for the discoveryservice has been set, taking default node flavor.")
        return None
    return desiredFlavor

def loadConfig(path):
    try:
        config = configparser.ConfigParser()
        config.read(path)
        return config
    except FileNotFoundError:
        print("Could not find config file at " + path)
        exit(-1)

'''
Assembles the initial cloud-config file for spawning nodes.
It uses a template located at ./yaml/cloud-config.yaml
'''
def prepareCloudConfig(configPath, tokenURL):
    try:
       file = open(configPath)
       yamlFile = yaml.load(file)
       yamlFile['coreos']['etcd2']['discovery'] = tokenURL
       modifiedYaml = yaml.dump(yamlFile)
       modifiedYaml = '#cloud-config\n\n' + modifiedYaml
       print(modifiedYaml)
       return modifiedYaml
    except FileNotFoundError:
        pass

'''
Uses REST API on a discovery service, to generate a discovery token for future nodes to use.
'''
def generateDiscoveryToken(discoveryDict, randomToken, size):
    print("Trying to create a discovery token on " + str(discoveryDict['floating']))
    tokenURL = 'http://' + str(discoveryDict['floating']) + ':4001' + TOKEN_SUFFIX + str(randomToken)
    if discoveryDict['newDiscovery']:
        print("The Discoveryservice has been recently created. Wait until its up.")
        sleep(30)
    for x in range(30):
        try:
            r = requests.put(tokenURL + '/_config/size', data={'value': str(size)})
            print("Generated discovery token..." + '\n' + r.text)
            break
        except:
            print("Could not generate token, retrying: " + str(x) + " from " + str(30))
            sleep(10)
            continue
    return 'http://' + str(discoveryDict['internal']) + ':4001' + TOKEN_SUFFIX + str(randomToken)


'''
Connect to openstack given security credentials.
'''
def connectOpenstack(OS_USERNAME, OS_PASSWORD, OS_TENANT_NAME, OS_AUTH_URL):
    try:
        nova = client.Client("2", OS_USERNAME, OS_PASSWORD, OS_TENANT_NAME, OS_AUTH_URL)
        print("Connected to " + OS_AUTH_URL)
        return nova
    except:
        print("Could not connect to Openstack...exiting")
        exit(-1)


'''
Build mandatory firewall group for all instances.
TODO: Use Neutron API to actually do that.
'''
def buildSecurityGroup(connection, id):
    securityGroup = connection.security_groups.get("7bf17971-183d-4d31-97fe-a5d17630056d")

    #Right now I can't create Egress Rules, so I have to cheat.
    '''
    #create the security group
    securityObject = connection.security_groups.create(str(id), "Autogenerated security group for this cluster.")
    #add rules
    connection.security_group_rules.create(securityObject.id, ip_protocol="icmp", from_port=-1, to_port=-1)
    connection.security_group_rules.create(securityObject.id, ip_protocol="tcp", from_port=4001, to_port=4001)
    connection.security_group_rules.create(securityObject.id, ip_protocol="tcp", from_port=2380, to_port=2380)
    connection.security_group_rules.create(securityObject.id, ip_protocol="tcp", from_port=2379, to_port=2379)
    connection.security_group_rules.create(securityObject.id, ip_protocol="tcp", from_port=22, to_port=22)
    '''
    return securityGroup

'''
Assigns a floating IP to an instance without obtaining network infos.
'''
def assignFloatingIPBlind(connection, instance, tenantName, floatingPool):
    floatingIPList = connection.floating_ips.list()
    freeFloatingIP = None
    for floatingIp in floatingIPList:
        if floatingIp.pool == floatingPool and floatingIp.fixed_ip is None:
            freeFloatingIp = floatingIp
            break
    if freeFloatingIp is None:
        print("FATAL: No free floating ip could be found...")
        exit(-1)
    print("Assigning following floating IP (may take a while): " + str(freeFloatingIp.ip))
    sleep(10)
    instance.add_floating_ip(freeFloatingIp.ip)
    return freeFloatingIp.ip

'''
Assign a floating IP to an instance and return network informations.
'''
def assignFloatingIP(connection, instance, tenantName, floatingPool):
    floatingIPList = connection.floating_ips.list()
    freeFloatingIP = None
    for floatingIp in floatingIPList:
        if floatingIp.pool == floatingPool and floatingIp.fixed_ip is None:
            freeFloatingIp = floatingIp
            break
    if freeFloatingIp is None:
        print("FATAL: No free floating ip could be found...")
        exit(-1)
    print("Assigning following floating IP (may take a while): " + str(freeFloatingIp.ip))
    sleep(10)
    instance.add_floating_ip(freeFloatingIp.ip)
    #print("Discovery Service has been started, it may need a while to fully boot up.")
    sleep(10)
    print("Discovery internal IP: " + str(instance.addresses[tenantName][0]['addr']))
    print("Discovery floating IP: " + str(freeFloatingIp.ip))
    return {'internal': instance.addresses[tenantName][0]['addr'],
            'floating': freeFloatingIp.ip,
            'newDiscovery': False,
            'discInstance': instance}

'''
Removes a floating ip form an instance.
'''
def removeFloatingIP(instance, ipToBeRemoved):
    try:
        instance.remove_floating_ip(ipToBeRemoved)
    except:
        print("Could not remove floating ip.")


'''
Returns an instance object given by the name of the instance.
'''
def getInstanceByName(instancePlan, instanceName):
    serverList = instancePlan['osConnection'].servers.list()
    for server in serverList:
        if server.name == instanceName:
            return server
    print("No Instance by the name: " + instanceName)


'''
Check if we have a discovery url in given config file, if not, set a service up
'''
def checkDiscoveryService(environmentDict, configFile, instancePlan):
    #Check if discovery service already exists...
    serverList = instancePlan['osConnection'].servers.list()
    tenantName = instancePlan['tenantName']
    floatingPool = instancePlan['floatingPool']
    for server in serverList:
        if server.name == 'CoreOS Discovery Service':
            if len(server.addresses[tenantName]) == 2:
                return  {'internal': server.addresses[tenantName][0]['addr'],
                         'floating': server.addresses[tenantName][1]['addr'],
                         'newDiscovery': False,
                         'discInstance': server}
            else:
                #print(len(server.addresses['bibiserv']))
                return assignFloatingIP(instancePlan['osConnection'], server, tenantName, floatingPool)
    try:
        discurl = {'superiorIP': configFile['discovery']['DISCOVERY_URL']}
        return discurl
    except KeyError:
        return None

'''
Builds an instance for discovery service, using etcd2 service from CoreOS.
'''
def createDiscoveryService(instancePlan):
    print('')
    print('------------------------------------')
    print("Setting up a discovery instance...")
    discoveryConfig = open(DISCOVERY_CONFIG_PATH)
    if instancePlan['discoveryFlavor'] is not None:
        flavor = instancePlan['discoveryFlavor']
    else:
        flavor = instancePlan['flavor']
    tenantName = instancePlan['tenantName']
    floatingPool = instancePlan['floatingPool']
    instanceName = "CoreOS Discovery Service"
    discServiceInstance = instancePlan['osConnection'].servers.create(instanceName,
                                                instancePlan['coreosImage'],
                                                flavor,
                                                nics=[{'net-id': instancePlan['standardNic'].id}],
                                                userdata=discoveryConfig,
                                                key_name=instancePlan['ssh_name'],
                                                security_groups=[instancePlan['securityGroup'].name])
    ipDict = assignFloatingIP(instancePlan['osConnection'], discServiceInstance, tenantName, floatingPool)
    ipDict['newDiscovery'] = True
    return ipDict

'''
Spawns all nodes.
'''
def createNodeInstance(instancePlan, count):
    print("Starting instance...")
    discServiceInstance = instancePlan['osConnection'].servers.create(instancePlan['ClusterName'],
                                                instancePlan['coreosImage'],
                                                instancePlan['flavor'],
                                                nics=[{'net-id': instancePlan['standardNic'].id}],
                                                userdata=instancePlan['cloudConfigYaml'],
                                                key_name=instancePlan['ssh_name'],
                                                min_count=count,
                                                max_count=count,
                                                security_groups=[instancePlan['securityGroup'].name])




if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("USAGE: python3 " + str(sys.argv[0]) + " [INI CONFIG PATH] [DESIRED NODE COUNT]" )
        exit(-1)

    #Gather parameters, maybe needs more defensive programming?
    INI_PATH = sys.argv[1]
    INSTANCE_COUNTS = int(sys.argv[2])

    #Generate RandomID for this cluster.
    clusterID = random.randint(1000, 999999)
    strClusterID = "CoreOS-" + str(clusterID)

    #Prepare Variables and parse config file.
    configFile = loadConfig(INI_PATH)
    environmentDict = createEnvironmentDict(configFile)

    #Establish a connection to Openstack
    instancePlan = {}
    instancePlan['osConnection'] = connectOpenstack(environmentDict['OS_USERNAME'],
                     environmentDict['OS_PASSWORD'],
                     environmentDict['OS_TENANT_NAME'],
                     environmentDict['OS_AUTH_URL'])
    instancePlan['ClusterName'] = strClusterID
    instancePlan['tenantName'] = environmentDict['OS_TENANT_NAME']
    instancePlan['floatingPool'] = environmentDict['FLOATING_IP_POOL']

    #Obtain ImageID
    instancePlan['coreosImage'] = obtain_coreos_image(instancePlan['osConnection'])

    #Build Security groups
    instancePlan['securityGroup'] = buildSecurityGroup(instancePlan['osConnection'], strClusterID)

    #Setup Network interface, must be put in list for nova api
    standardNic = obtainNIC(instancePlan['osConnection'], environmentDict['OS_TENANT_NAME'])
    instancePlan['standardNic'] = standardNic

    #Obtain Flavors
    instancePlan['flavor'] = obtainDesiredFlavor(instancePlan['osConnection'], environmentDict['OS_FLAVOR'])
    instancePlan['discoveryFlavor'] = getDiscoveryFlavour(instancePlan['osConnection'], configFile)

    #SSH Stuff
    instancePlan['ssh_name'] = environmentDict['OS_SSH_NAME']


    #Make sure we have a discovery service running
    discoveryIPdict = checkDiscoveryService(environmentDict, configFile, instancePlan)
    if discoveryIPdict is None:
        discoveryIPdict = createDiscoveryService(instancePlan)

    #Generate a discovery token, given the name of the cluster and the number of wished nodes.
    tokenURL = generateDiscoveryToken(discoveryIPdict, strClusterID, INSTANCE_COUNTS)

    #No need for a floating ip for the discovery service, after we got a token.
    removeFloatingIP(discoveryIPdict['discInstance'], discoveryIPdict['floating'])

    #Assemble the initial cloud-config for the cluster, with the freshly generated token.
    instancePlan['cloudConfigYaml'] = prepareCloudConfig(CLOUD_CONFIG_PATH, tokenURL)

    #Now we are ready to spawn all the instances, given the build plan and the amount of desired nodes.
    createNodeInstance(instancePlan, INSTANCE_COUNTS)

    #For comfort, we want to give the first spawned node a floating ip.
    firstNode = getInstanceByName(instancePlan, strClusterID+"-1")

    #Assign floating ip to first node
    print("Adding floating IP to first node of the cluster...")
    firstNodeIP = assignFloatingIPBlind(instancePlan['osConnection'],
                     firstNode,
                     instancePlan['tenantName'],
                     instancePlan['floatingPool'])

    #The war is ours! ^o^
    print("-----------------------------------------------------------------------------")
    print("You can now SSH into a node with your SSH Key to core@" + str(firstNodeIP))
    print("Have a nice day!")
    exit(0)


