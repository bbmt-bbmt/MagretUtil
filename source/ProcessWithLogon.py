import ctypes
from ctypes.wintypes import WORD, DWORD, LPSTR, HANDLE

NULL  = 0
TRUE  = 1
FALSE = 0

INVALID_HANDLE_VALUE = -1

#WORD   = ctypes.c_ushort
#DWORD  = ctypes.c_uint
#LPSTR  = ctypes.c_char_p
#LPBYTE = LPSTR
#HANDLE = DWORD

# typedef struct _PROCESS_INFORMATION {
#     HANDLE hProcess;
#     HANDLE hThread;
#     DWORD dwProcessId;
#     DWORD dwThreadId;
# } PROCESS_INFORMATION, *PPROCESS_INFORMATION, *LPPROCESS_INFORMATION;
class PROCESS_INFORMATION(ctypes.Structure):
   _pack_   = 1
   _fields_ = [
       ('hProcess',    HANDLE),
       ('hThread',     HANDLE),
       ('dwProcessId', DWORD),
       ('dwThreadId',  DWORD),
   ]

# typedef struct _STARTUPINFO {
#     DWORD   cb;
#     LPSTR   lpReserved;
#     LPSTR   lpDesktop;
#     LPSTR   lpTitle;
#     DWORD   dwX;
#     DWORD   dwY;
#     DWORD   dwXSize;
#     DWORD   dwYSize;
#     DWORD   dwXCountChars;
#     DWORD   dwYCountChars;
#     DWORD   dwFillAttribute;
#     DWORD   dwFlags;
#     WORD    wShowWindow;
#     WORD    cbReserved2;
#     LPBYTE  lpReserved2;
#     HANDLE  hStdInput;
#     HANDLE  hStdOutput;
#     HANDLE  hStdError;
# } STARTUPINFO, *LPSTARTUPINFO;
class STARTUPINFO(ctypes.Structure):
   _pack_   = 1
   _fields_ = [
       ('cb',              DWORD),
       ('lpReserved',      DWORD),     # LPSTR
       ('lpDesktop',       LPSTR),
       ('lpTitle',         ctypes.c_wchar_p), #dans la version original LPSTR mais ne marche pas
       ('dwX',             DWORD),
       ('dwY',             DWORD),
       ('dwXSize',         DWORD),
       ('dwYSize',         DWORD),
       ('dwXCountChars',   DWORD),
       ('dwYCountChars',   DWORD),
       ('dwFillAttribute', DWORD),
       ('dwFlags',         DWORD),
       ('wShowWindow',     WORD),
       ('cbReserved2',     WORD),
       ('lpReserved2',     DWORD),     # LPBYTE
       ('hStdInput',       DWORD),
       ('hStdOutput',      DWORD),
       ('hStdError',       DWORD),
   ]

# BOOL WINAPI CreateProcessWithLogonW(
#   __in         LPCWSTR lpUsername,
#   __in_opt     LPCWSTR lpDomain,
#   __in         LPCWSTR lpPassword,
#   __in         DWORD dwLogonFlags,
#   __in_opt     LPCWSTR lpApplicationName,
#   __inout_opt  LPWSTR lpCommandLine,
#   __in         DWORD dwCreationFlags,
#   __in_opt     LPVOID lpEnvironment,
#   __in_opt     LPCWSTR lpCurrentDirectory,
#   __in         LPSTARTUPINFOW lpStartupInfo,
#   __out        LPPROCESS_INFORMATION lpProcessInfo
# );
def CreateProcessWithLogonW(lpUsername = None, lpDomain = None, lpPassword =
None, dwLogonFlags = 0, lpApplicationName = None, lpCommandLine = None,
dwCreationFlags = 0, lpEnvironment = None, lpCurrentDirectory = None,
lpStartupInfo = None):
   if not lpUsername:
       lpUsername          = NULL
   else:
       lpUsername          = ctypes.c_wchar_p(lpUsername)
   if not lpDomain:
       lpDomain            = NULL
   else:
       lpDomain            = ctypes.c_wchar_p(lpDomain)
   if not lpPassword:
       lpPassword          = NULL
   else:
       lpPassword          = ctypes.c_wchar_p(lpPassword)
   if not lpApplicationName:
       lpApplicationName   = NULL
   else:
       lpApplicationName   = ctypes.c_wchar_p(lpApplicationName)
   if not lpCommandLine:
       lpCommandLine       = NULL
   else:
       lpCommandLine       = ctypes.create_unicode_buffer(lpCommandLine)
   if not lpEnvironment:
       lpEnvironment       = NULL
   else:
       lpEnvironment       = ctypes.c_wchar_p(lpEnvironment)
   if not lpCurrentDirectory:
       lpCurrentDirectory  = NULL
   else:
       lpCurrentDirectory  = ctypes.c_wchar_p(lpCurrentDirectory)
   if not lpStartupInfo:
       lpStartupInfo              = STARTUPINFO()
       lpStartupInfo.cb           = ctypes.sizeof(STARTUPINFO)
       lpStartupInfo.lpReserved   = 0
       lpStartupInfo.lpDesktop    = 0
       lpStartupInfo.lpTitle      = 0
       lpStartupInfo.dwFlags      = 0
       lpStartupInfo.cbReserved2  = 0
       lpStartupInfo.lpReserved2  = 0
   lpProcessInformation              = PROCESS_INFORMATION()
   lpProcessInformation.hProcess     = INVALID_HANDLE_VALUE
   lpProcessInformation.hThread      = INVALID_HANDLE_VALUE
   lpProcessInformation.dwProcessId  = 0
   lpProcessInformation.dwThreadId   = 0
   success = ctypes.windll.advapi32.CreateProcessWithLogonW(lpUsername,
lpDomain, lpPassword, dwLogonFlags, lpApplicationName,
ctypes.byref(lpCommandLine), dwCreationFlags, lpEnvironment,
lpCurrentDirectory, ctypes.byref(lpStartupInfo),
ctypes.byref(lpProcessInformation))
   if success == FALSE:
       raise ctypes.WinError()
   return lpProcessInformation

