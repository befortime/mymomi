import sys
sys.path.append('/Users/Yasmine/kino/pylibs')

print(sys.version)
PY3 = sys.version > '3'

import atexit
import ssl
if PY3:
    from http import cookies as Cookie
else:
    import Cookie

import pyVmomi
from pyVim import connect
from pyVmomi import vim, pbm
from pyVim.task import WaitForTask

import vsanmgmtObjects

import vsanapiutils

log_level = 5

vcIp = '10.160.173.97'
vcUser = 'administrator@vsphere.local'
vcPass = 'Admin!23'


def Debug(*args, **kwargs):
    if log_level > 4:
        print(*args, **kwargs)

def Info(*args, **kwargs):
    if log_level > 2:
        print(*args, **kwargs)

def ConnectToVsanClusterConfigSystem(stub, context=None):
    # sessionCookie = stub.cookie.split('"')[1]
    # httpContext = pyVmomi.VmomiSupport.GetHttpContext()
    # cookieObj = Cookie.SimpleCookie()
    # cookieObj["vmware_soap_session"] = sessionCookie
    # httpContext["cookies"] = cookieObj
    hostname = stub.host.split(":")[0]
    vccsStub = pyVmomi.SoapStubAdapter(host=hostname,
                                      version = "vim.version.version11",
                                      path = "/vsanHealth",
                                      sslContext = connect)
    vccsStub.cookie = stub.cookie
    vccs = vim.cluster.VsanVcClusterHealthSystem("vsan-cluster-config-system", vccsStub)
    return vccs



if __name__ == '__main__':
    context = None
    if hasattr(ssl, '_create_unverified_context'):
        context = ssl._create_unverified_context()

    si = connect.SmartConnect(host=vcIp,
                            user=vcUser,
                            pwd=vcPass,
                            port=443,
                            sslContext=context)

    if not si:
        Info("Failed to connect VC: {0}".format(vcUser))
    else:
        Info("Connect VC {0} succeed".format(vcUser))

    atexit.register(connect.Disconnect, si)

    cluster = None
    for entity in si.content.rootFolder.childEntity[0].hostFolder.childEntity:
        if type(entity) == vim.ClusterComputeResource:
            cluster = entity
    Debug(cluster.name)

    vsanVcMos = vsanapiutils.GetVsanVcMos(si._stub, context=context)

    vccs = vsanVcMos['vsan-cluster-config-system']
    clusterConfig = vccs.GetConfigInfoEx(cluster)
    Info(clusterConfig.iscsiConfig.enabled)

    pbmSi, pbmContent = vsanapiutils.GetPbmConnection(si._stub, context=context)

    pm = pbmContent.profileManager
    profileIds = pm.PbmQueryProfile(
        resourceType=pbm.profile.ResourceType(resourceType="STORAGE"),
        profileCategory="REQUIREMENT"
    )

    profiles = []
    if len(profileIds) > 0:
        profiles = pm.PbmRetrieveContent(profileIds=profileIds)

    # Attempt to find profile name given by user
    for profile in profiles:
        if profile.name == 'vSAN Default Storage Policy':
            vitProfile = profile
            break

    policyId = vitProfile.profileId.uniqueId
    policySpec = vim.VirtualMachineDefinedProfileSpec(profileId=policyId)

    serviceSpec = vim.cluster.VsanIscsiTargetServiceSpec(defaultConfig = vim.cluster.VsanIscsiTargetServiceDefaultConfigSpec(
                                        networkInterface = "vmk0"),
                                        homeObjectStoragePolicy = policySpec,
                                        enabled = True)

    task = vccs.ReconfigureEx(cluster, vim.vsan.ReconfigSpec(iscsiSpec = serviceSpec))

    task = vim.task(task._moId, cluster._stub)
    WaitForTask(task)