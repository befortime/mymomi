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
from pyVmomi import vim

import vsanmgmtObjects

import vsanapiutils

log_level = 5

vcIp = '10.160.251.57'
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
