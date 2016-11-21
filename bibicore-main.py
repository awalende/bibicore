from novaclient import client
import os
import yaml



#Obtaining Environmentvariables for nova
OS_USERNAME = os.environ['OS_USERNAME']
OS_PASSWORD = os.environ['OS_PASSWORD']
OS_AUTH_URL = os.environ['OS_AUTH_URL']
OS_TENANT_NAME = os.environ['OS_TENANT_NAME']


#check and overwrite variables
def lookUpVariables():
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




