from novaclient import client
import os
import configparser
import yaml



#Obtaining Environmentvariables for nova
OS_USERNAME = os.environ['OS_USERNAME']
OS_PASSWORD = os.environ['OS_PASSWORD']
OS_AUTH_URL = os.environ['OS_AUTH_URL']
OS_TENANT_NAME = os.environ['OS_TENANT_NAME']

OS_NICNAME = "bibiserv"
OS_FLAVOUR = "c1r8d49"
SSH_KEY = ""




#check and overwrite variables
def validateVariables():
    pass



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
    pass

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
    nova = connectOpenstack()
    print("....it worked!")
    obtainDesiredFlavor(nova)




