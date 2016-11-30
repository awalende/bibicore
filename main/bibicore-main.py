from novaclient import client
import os
import configparser
import yaml
import random


OS_NICNAME = "bibiserv"
OS_FLAVOUR = "c1r8d49"

'''
TODO:
Parse config file from args.
Customize cloud config yaml
Figure out SSH.
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
                    print("Key named " + item[0] + " not found in OS or config file...exiting")
                    exit(-1)
        #print(item[0] + " seems to be properly set.")
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


def loadCloudConfig():
    pass



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




if __name__ == '__main__':
    #Generate RandomID for this cluster.
    clusterID = random.randint(1000, 999999)
    strClusterID = "CoreOS-" + str(clusterID)
    #Prepare Variables and parse config file.
    configFile = loadConfig("config/example_empty.ini")
    environmentDict = createEnvironmentDict(configFile)
    #Establish a connection to Openstack
    osConnection = connectOpenstack(environmentDict['OS_USERNAME'],
                     environmentDict['OS_PASSWORD'],
                     environmentDict['OS_TENANT_NAME'],
                     environmentDict['OS_AUTH_URL'])

    #Build Security groups
    securityGroup = buildSecurityGroup(osConnection, strClusterID)

    #testcreate
    standardNic = obtainNIC(osConnection)
    standradNicList = []
    standradNicList.append(standardNic)


    #Why the hell do I have to put this in dict list
    #osConnection.servers.create("test111", obtain_coreos_image(osConnection), obtainDesiredFlavor(osConnection), nics=[{'net-id': standardNic.id}])








