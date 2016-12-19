from novaclient import client
from time import sleep
import os
import configparser
import yaml
import random
import requests


OS_NICNAME = "bibiserv"
OS_FLAVOUR = "c1r8d40"
CLOUD_CONFIG_PATH="yaml/cloud-config.yaml"
DISCOVERY_CONFIG_PATH = "yaml/discovery.yaml"

TOKEN_TIMEOUT=10
TOKEN_SUFFIX='/v2/keys/_etcd/registry/'


'''
TODO:
Dissasociate floating ip after token is generated.
At end of script, set floating IP to first node and give ip-info to user.
Remove hardcoded stuff.
Give some love to the config file.
Write Readme.
'''


def checkEnvironmentFromOS(key):
    return key in os.environ

def validateEnvironmentDict(dict, configFile):
    newDict = {}
    itemList = dict.items()
    for item in itemList:
        if item[1] == "":
            print(item[0] + " is not set, looking for environment variable from OS.")
            if checkEnvironmentFromOS(item[0]):
                print("Found corresponding environment variable!")
                newDict[item[0]] = os.environ[item[0]]
                continue
            else:
                print("Looking for variable in .ini file...")
                try:
                    newDict[item[0]] = configFile['config'][item[0]]
                    print("..found key in config file!")

                    continue
                except KeyError:
                    print("Key named " + item[0] + " not found in OS or config file!")
        newDict[item[0]] = item[1]
    newDict = setSSH(newDict, configFile)
    return newDict


#check and overwrite variables
def createEnvironmentDict(configFile):
    #needs to be cleaned up after debugging
    environmentDict = {}
    environmentDict['OS_USERNAME'] = ""
    environmentDict['OS_PASSWORD'] = ""
    environmentDict['OS_AUTH_URL'] = ""
    environmentDict['OS_TENANT_NAME'] = ""
    environmentDict['OS_NICNAME'] = OS_NICNAME
    environmentDict['OS_FLAVOR'] = OS_FLAVOUR
    environmentDict['SSH_KEY'] = ''
    environmentDict['DISCOVERY_URL'] = ''
    environmentDict = validateEnvironmentDict(environmentDict, configFile)
    return environmentDict



def obtain_coreos_image(connection):
    imageList = connection.images.list()
    for image in imageList:
        if "CoreOS" in image.name:
            print("Found CoreOS Image: " + image.name)
            return image
    print("Could not find any CoreOS Image...exiting.")
    exit(-1)


def obtainNIC(connection, NICName=OS_NICNAME):
    nicList = connection.networks.list()
    for network in nicList:
        if network.label == NICName:
            print("Found network: " + network.label)
            return network
    print("Could not find network! Following networks are available:")
    print(nicList)
    exit(-1)


def obtainDesiredFlavor(connection, flavorName=OS_FLAVOUR):
    flavorList = connection.flavors.list()
    for flavor in flavorList:
        if flavor.name == flavorName:
            print("Found desired flavor: " + flavor.name)
            return flavor
    print("Could not find flavor! Following flavors are available:")
    print(flavorList)
    exit(-1)

def setSSH(dict, configFile):
    #Maybe give support for manual ssh key input
    try:
        dict['SSH_KEY'] = configFile['security']['OS_SSHKEYPAIR']
    except KeyError:
        print("WARNING: No SSH Keypair could be set for the instances, you may have difficulties logging in with ssh.")
    return dict

def loadConfig(path):
    try:
        config = configparser.ConfigParser()
        config.read(path)
        return config
    except FileNotFoundError:
        print("Could not find config file at " + path)
        exit(-1)


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


def connectOpenstack(OS_USERNAME, OS_PASSWORD, OS_TENANT_NAME, OS_AUTH_URL):
    try:
        nova = client.Client("2", OS_USERNAME, OS_PASSWORD, OS_TENANT_NAME, OS_AUTH_URL)
        print("Connected to " + OS_AUTH_URL)
        return nova
    except:
        print("Could not connect to Openstack...exiting")
        exit(-1)


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


def assignFloatingIP(connection, instance):
    floatingIPList = connection.floating_ips.list()
    freeFloatingIP = None
    for floatingIp in floatingIPList:
        if floatingIp.pool == 'cebitec' and floatingIp.fixed_ip is None:
            freeFloatingIp = floatingIp
            break
    if freeFloatingIp is None:
        print("FATAL: No free floating ip could be found...")
        exit(-1)
    print("Assigning following floating IP (may take a while): " + str(freeFloatingIp.ip))
    sleep(10)
    instance.add_floating_ip(freeFloatingIp.ip)
    #print("Discovery Service has been started, it may need a while to fully boot up.")
    #TODO: REMOVE HARDCODED TENANTNAME
    sleep(10)
    print("Discovery internal IP: " + str(instance.addresses['bibiserv'][0]['addr']))
    print("Discovery floating IP: " + str(freeFloatingIp.ip))
    return {'internal': instance.addresses['bibiserv'][0]['addr'],
            'floating': freeFloatingIp.ip,
            'newDiscovery': False}


'''
Check if we have a discovery url in given config file, if not, set a service up
'''
def checkDiscoveryService(environmentDict, configFile, instancePlan):
    #Check if discovery service already exists...
    serverList = instancePlan['osConnection'].servers.list()
    for server in serverList:
        if server.name == 'CoreOS Discovery Service':
            if len(server.addresses['bibiserv']) == 2:
                return  {'internal': server.addresses['bibiserv'][0]['addr'],
                         'floating': server.addresses['bibiserv'][1]['addr'],
                         'newDiscovery': False}
            else:
                #print(len(server.addresses['bibiserv']))
                return assignFloatingIP(instancePlan['osConnection'], server)
    try:
        discurl = {'superiorIP': configFile['discovery']['DISCOVERY_URL']}
        return discurl
    except KeyError:
        return None

def createDiscoveryService(instancePlan):
    print('')
    print('------------------------------------')
    print("Setting up a discovery instance...")
    discoveryConfig = open(DISCOVERY_CONFIG_PATH)
    instanceName = "CoreOS Discovery Service"
    #TODO: Keyname support in config file
    discServiceInstance = instancePlan['osConnection'].servers.create(instanceName,
                                                instancePlan['coreosImage'],
                                                instancePlan['flavor'],
                                                nics=[{'net-id': instancePlan['standardNic'].id}],
                                                userdata=discoveryConfig,
                                                key_name='awalende',
                                                security_groups=[instancePlan['securityGroup'].name])
    ipDict = assignFloatingIP(instancePlan['osConnection'], discServiceInstance)
    ipDict['newDiscovery'] = True
    return ipDict


def createNodeInstance(instancePlan, count):
    print("Starting instance...")
    discServiceInstance = instancePlan['osConnection'].servers.create(instancePlan['ClusterName'] + 'node',
                                                instancePlan['coreosImage'],
                                                instancePlan['flavor'],
                                                nics=[{'net-id': instancePlan['standardNic'].id}],
                                                userdata=instancePlan['cloudConfigYaml'],
                                                key_name='awalende',
                                                min_count=count,
                                                max_count=count,
                                                security_groups=[instancePlan['securityGroup'].name])



if __name__ == '__main__':
    #Generate RandomID for this cluster.
    clusterID = random.randint(1000, 999999)
    strClusterID = "CoreOS-" + str(clusterID)
    #Prepare Variables and parse config file.
    configFile = loadConfig("/home/awalende/config.ini")
    environmentDict = createEnvironmentDict(configFile)
    #Establish a connection to Openstack
    instancePlan = {}
    instancePlan['osConnection'] = connectOpenstack(environmentDict['OS_USERNAME'],
                     environmentDict['OS_PASSWORD'],
                     environmentDict['OS_TENANT_NAME'],
                     environmentDict['OS_AUTH_URL'])
    instancePlan['ClusterName'] = strClusterID

    #Obtain ImageID
    instancePlan['coreosImage'] = obtain_coreos_image(instancePlan['osConnection'])

    #Build Security groups
    instancePlan['securityGroup'] = buildSecurityGroup(instancePlan['osConnection'], strClusterID)

    #Setup Network interface, must be put in list for nova api
    standardNic = obtainNIC(instancePlan['osConnection'])
    instancePlan['standardNic'] = standardNic

    #Obtain Flavor
    instancePlan['flavor'] = obtainDesiredFlavor(instancePlan['osConnection'])


    #Make sure we have a discovery service running
    discoveryIPdict = checkDiscoveryService(environmentDict, configFile, instancePlan)
    if discoveryIPdict is None:
        discoveryIPdict = createDiscoveryService(instancePlan)

    #TODO: Parameterize instance count
    tokenURL = generateDiscoveryToken(discoveryIPdict, strClusterID, 3)
    instancePlan['cloudConfigYaml'] = prepareCloudConfig(CLOUD_CONFIG_PATH, tokenURL)


    createNodeInstance(instancePlan, 3)

