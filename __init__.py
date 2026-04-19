def classFactory(iface):
    from .src.main import SMaRCMissionControlPlugin

    return SMaRCMissionControlPlugin(iface)
