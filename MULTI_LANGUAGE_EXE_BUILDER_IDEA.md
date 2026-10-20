Multi-Language EXE Builder Idea
Extend the existing Windows 11 Python EXE Builder with selectable build modes instead of making separate tools.
Build modes
Mode	Input	Build engine	Typical output
Python	Python script/project	PyInstaller workflow	Packaged Windows executable
C#/.NET	.csproj	.NET publish workflow	Framework-dependent or self-contained executable


Interface concept
Use a top-level toggle:
Build mode:  Python EXE  |  C# .NET Publish
The application switches to a smaller, mode-specific panel instead of showing every setting at once.
C#/.NET publish panel
- Choose a .csproj file
- Choose output folder and executable name
- Target runtime: win-x64 or win-arm64
- Self-contained toggle
- Single-file toggle
- Optional trim toggle
- Choose .ico application icon
- Publish and open-output-folder actions
bin/ and obj/ are disposable .NET build output and should remain ignored by Git.
Product value
One familiar builder can support two practical paths:
- Python for existing scripts and PyInstaller packaging
- C# for polished Windows GUI utilities with built-in .NET publishing
AutoHotkey is out of scope because it already has its own script-to-executable utility.


1:18 AM