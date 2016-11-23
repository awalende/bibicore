from novaclient import client
import os
import configparser
import yaml


OS_NICNAME = "bibiserv"
OS_FLAVOUR = "c1r8d49"
SSH_KEY = ""


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
    #print(newDict)
    return newDict



#check and overwrite variables
def setupEnvironmentDict(configFile):
    #needs to be cleaned up after debugging
    environmentDict = {}
    environmentDict['OS_USERNAME'] = ""
    environmentDict['OS_PASSWORD'] = ""
    environmentDict['OS_AUTH_URL'] = ""
    environmentDict['OS_TENANT_NAME'] = ""
    environmentDict['OS_NICNAME'] = OS_NICNAME
    environmentDict['OS_FLAVOR'] = OS_FLAVOUR
    environmentDict['SSH_KEY'] = SSH_KEY
    environmentDict = validateEnvironmentDict(environmentDict, configFile)
    print(environmentDict)
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
        if network.name == NICName:
            print("Found network: " + network.name)
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

def setSSH():
    pass


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



def connectOpenstack():
    try:
        nova = client.Client("2", OS_USERNAME, OS_PASSWORD, OS_TENANT_NAME, OS_AUTH_URL)
        return nova
    except:
        print("Could not connect to Openstack...exiting")
        exit(-1)


if __name__ == '__main__':
    print("Trying to connect to Openstack...")
    #nova = connectOpenstack()
    print("....it worked!")
    #obtainDesiredFlavor(nova)
    configFile = loadConfig("config/example.ini")
    setupEnvironmentDict(configFile)




