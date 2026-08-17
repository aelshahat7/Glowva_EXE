; Glowva ERP - Inno Setup installer script
; ===========================================
; يتطلب: Inno Setup (مجاني) من https://jrsoftware.org/isdl.php
; خطوات الاستخدام:
;   1. شغّلي build_exe.bat الأول (بيعمل dist\GlowvaERP.exe)
;   2. افتحي الملف ده في Inno Setup Compiler
;   3. دوسي Build -> Compile
;   4. هتلاقي GlowvaERP_Setup.exe جاهز في مجلد Output

#define MyAppName "Glowva ERP"
#define MyAppVersion "1.0"
#define MyAppExeName "GlowvaERP.exe"

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\GlowvaERP
DefaultGroupName={#MyAppName}
OutputBaseFilename=GlowvaERP_Setup
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "أنشئ أيقونة على سطح المكتب"; GroupDescription: "أيقونات إضافية:"

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{group}\إلغاء تثبيت {#MyAppName}"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "تشغيل {#MyAppName}"; Flags: postinstall nowait skipifsilent
