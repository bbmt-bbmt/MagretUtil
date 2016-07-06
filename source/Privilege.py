#! python3
# coding: utf-8

import win32con
import sys
import os
import ctypes
from ProcessWithLogon import CreateProcessWithLogonW
from ProcessWithLogon import STARTUPINFO

from win32com.shell.shell import ShellExecuteEx
from win32com.shell import shellcon


def get_privilege(login, password, domaine=None, uac=False):
    lpStartupInfo = STARTUPINFO()
    lpStartupInfo.cb = ctypes.sizeof(STARTUPINFO)
    lpStartupInfo.lpReserved = 0
    lpStartupInfo.lpDesktop = 0
    lpStartupInfo.lpTitle = 0  # ctypes.c_wchar_p('mon titre')
    lpStartupInfo.dwFlags = 0  # win32con.STARTF_USESHOWWINDOW
    lpStartupInfo.cbReserved2 = 0
    lpStartupInfo.lpReserved2 = 0
    lpStartupInfo.wShowWindow = win32con.SW_HIDE
    pass_uac = ''
    if uac:
        pass_uac = 'pass_uac'
        lpStartupInfo.dwFlags = win32con.STARTF_USESHOWWINDOW
    # cmd = 'cmd.exe /C "cd /D \"%s\" & \"%s\" %s"' % (os.getcwd(), sys.argv[0], pass_uac)
    name = sys.argv[0].split('\\')[-1]
    path = os.getcwd()
    # changer de repertoire permet de lancer pushd sans erreur
    os.chdir("c:\\")
    new_cmd = 'cmd /C "pushd %s && \"%s\" %s"' % (path, name, pass_uac)

    CreateProcessWithLogonW(login, domaine, password, 0, None,
                            new_cmd, lpStartupInfo=lpStartupInfo)


def pass_uac():
    ShellExecuteEx(nShow=win32con.SW_SHOWNORMAL, fMask=shellcon.SEE_MASK_NOCLOSEPROCESS, lpVerb='runas', lpFile=sys.argv[0])
    return
