param(
    [Parameter(Mandatory=$true)][string]$PayloadBase64,
    [switch]$RegisterOnly,
    [string]$ShortcutPath
)
$ErrorActionPreference = 'Stop'
try {
    $config = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($PayloadBase64)) | ConvertFrom-Json
    $appId = 'TelegramNotifier.Desktop'
    if (-not $ShortcutPath) {
        $ShortcutPath = Join-Path ([Environment]::GetFolderPath('Programs')) 'Telegram Notifier.lnk'
    }
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($ShortcutPath)
    $shortcut.TargetPath = $config.python
    $shortcut.Arguments = $config.arguments
    $shortcut.WorkingDirectory = Split-Path -Parent $config.app
    $shortcut.Description = 'Telegram online and typing notifications'
    $shortcut.Save()
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class TelegramNotificationIdentity {
    [StructLayout(LayoutKind.Sequential, Pack=4)]
    public struct PropertyKey { public Guid format; public uint id; }
    [StructLayout(LayoutKind.Explicit, Size=24)]
    public struct PropVariant {
        [FieldOffset(0)] public ushort type;
        [FieldOffset(8)] public IntPtr text;
    }
    [ComImport, Guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    public interface IPropertyStore {
        [PreserveSig] int GetCount(out uint count);
        [PreserveSig] int GetAt(uint index, out PropertyKey key);
        [PreserveSig] int GetValue(ref PropertyKey key, out PropVariant value);
        [PreserveSig] int SetValue(ref PropertyKey key, ref PropVariant value);
        [PreserveSig] int Commit();
    }
    [DllImport("shell32.dll", CharSet=CharSet.Unicode, PreserveSig=true)]
    static extern int SHGetPropertyStoreFromParsingName(string path, IntPtr context, uint flags,
        ref Guid iid, [MarshalAs(UnmanagedType.Interface)] out IPropertyStore store);
    [DllImport("shell32.dll", CharSet=CharSet.Unicode)]
    static extern int SetCurrentProcessExplicitAppUserModelID(string appId);
    public static void Register(string path, string appId) {
        Guid iid = new Guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99");
        IPropertyStore store;
        Marshal.ThrowExceptionForHR(SHGetPropertyStoreFromParsingName(path, IntPtr.Zero, 2, ref iid, out store));
        PropVariant value = new PropVariant { type = 31, text = Marshal.StringToCoTaskMemUni(appId) };
        try {
            PropertyKey key = new PropertyKey { format = new Guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"), id = 5 };
            Marshal.ThrowExceptionForHR(store.SetValue(ref key, ref value));
            Marshal.ThrowExceptionForHR(store.Commit());
            Marshal.ThrowExceptionForHR(SetCurrentProcessExplicitAppUserModelID(appId));
        } finally {
            Marshal.FreeCoTaskMem(value.text);
            Marshal.ReleaseComObject(store);
        }
    }
}
'@
    [TelegramNotificationIdentity]::Register($ShortcutPath, $appId)
    if ($RegisterOnly) { Write-Output 'registered'; exit 0 }
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime] > $null
    [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType=WindowsRuntime] > $null
    $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($appId)
    $setting = $notifier.Setting.ToString()
    if ($setting -ne 'Enabled') {
        throw "Windows notifications are blocked ($setting). Check Settings > System > Notifications."
    }
    $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
    $xml.LoadXml($config.xml)
    $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
    $notifier.Show($toast)
    Write-Output 'submitted'
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 1
}
