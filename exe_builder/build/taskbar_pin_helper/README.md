# Taskbar pin helper

`PinWindow.cs` is the C# helper that finds Explorer's context menus and invokes
their named actions. `TaskbarPinHelper.csproj` lets you open and build the code
as a C# class library using the .NET 10 Windows desktop SDK.

The builder does not run the compiled library. `taskbar_pin.py` reads the same
`PinWindow.cs` file and passes it to Windows PowerShell, which compiles it in
memory with `Add-Type`. The surrounding PowerShell script selects the built
executable and calls the helper; Python runs that script in a background process
and writes its progress to the build log.

When packaging the builder, include `PinWindow.cs` at
`exe_builder/build/taskbar_pin_helper/PinWindow.cs` in the bundled data.
