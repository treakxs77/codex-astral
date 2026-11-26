param([string]$BlishExe,[string]$SourceDirectory,[string]$OfficialPackage,[string]$OutputDirectory,[string]$Version='1.14.4')
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem
$taskRoot = $PSScriptRoot
$source = $SourceDirectory
if(!$source){$source=Join-Path $taskRoot 'Pathing-1.14.4'}
$build = Join-Path $taskRoot 'Build'
if($OutputDirectory){$build=Join-Path $OutputDirectory 'Build'}
$refs = Join-Path $build 'references'
$resources = Join-Path $build 'resources'
$stage = Join-Path $build 'package'
$packs = [IO.Path]::GetFullPath((Join-Path $taskRoot '..\..\Codex Astral et Forge de Tyrie\Forge-Packs'))
$official=$OfficialPackage
if(!$official){$official=[IO.Path]::GetFullPath((Join-Path $taskRoot '..\..\Test-157-forge\Pathing-1.14.4-Officiel.bhm'))}
if($OutputDirectory){$packs=$OutputDirectory}
foreach ($dir in @($build,$refs,$resources,$stage)) { [IO.Directory]::CreateDirectory($dir) | Out-Null }
$zip = [IO.Compression.ZipFile]::OpenRead($official)
try {
    foreach ($entry in $zip.Entries) {
        if ($entry.Name -eq '') { continue }
        $target = Join-Path $stage $entry.FullName
        [IO.Directory]::CreateDirectory((Split-Path $target)) | Out-Null
        [IO.Compression.ZipFileExtensions]::ExtractToFile($entry,$target,$true)
    }
} finally { $zip.Dispose() }
$hostAssembly = [Reflection.Assembly]::ReflectionOnlyLoadFrom($BlishExe)
foreach ($name in $hostAssembly.GetManifestResourceNames()) {
    if ($name -match '^costura\.(.*\.dll)\.compressed$') {
        $target = Join-Path $refs $Matches[1]
        $inputStream = $hostAssembly.GetManifestResourceStream($name)
        $deflate = New-Object IO.Compression.DeflateStream($inputStream,[IO.Compression.CompressionMode]::Decompress)
        $outputStream = [IO.File]::Create($target)
        try { $deflate.CopyTo($outputStream) } finally { $outputStream.Dispose(); $deflate.Dispose(); $inputStream.Dispose() }
    }
}
Copy-Item -LiteralPath $BlishExe -Destination (Join-Path $refs 'Blish HUD.exe') -Force
Get-ChildItem -LiteralPath $stage -File -Filter '*.dll' | Where-Object Name -ne 'Pathing.dll' | Copy-Item -Destination $refs -Force
$originalAssembly = [Reflection.Assembly]::ReflectionOnlyLoad([IO.File]::ReadAllBytes((Join-Path $stage 'Pathing.dll')))
foreach ($name in $originalAssembly.GetManifestResourceNames()) {
    $inputStream = $originalAssembly.GetManifestResourceStream($name)
    $outputStream = [IO.File]::Create((Join-Path $resources $name))
    try { $inputStream.CopyTo($outputStream) } finally { $outputStream.Dispose(); $inputStream.Dispose() }
}
function Write-Strings([string]$Resx,[string]$OutputPath) {
    [xml]$xml = [IO.File]::ReadAllText($Resx)
    $writer = New-Object Resources.ResourceWriter($OutputPath)
    try { foreach ($item in $xml.root.data) { $writer.AddResource([string]$item.name,[string]$item.value) } }
    finally { $writer.Dispose() }
}
Write-Strings (Join-Path $source 'Strings.resx') (Join-Path $resources 'BhModule.Community.Pathing.Strings.resources')
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
$compiler = & $vswhere -latest -products '*' -find 'MSBuild\**\Bin\Roslyn\csc.exe' | Select-Object -First 1
if (!$compiler) { throw 'Compilateur C# Roslyn introuvable.' }
$lines = New-Object 'Collections.Generic.List[string]'
$lines.AddRange([string[]]@('/nologo','/target:library','/langversion:latest','/platform:x64','/unsafe','/optimize+','/deterministic+','/debug:portable','/codepage:65001',('/out:"'+(Join-Path $build 'Pathing.dll')+'"')))
foreach ($reference in (Get-ChildItem -LiteralPath $refs -File | Where-Object { $_.Extension -eq '.dll' -or $_.Name -eq 'Blish HUD.exe' })) { $lines.Add('/r:"'+$reference.FullName+'"') }
$facade = Get-ChildItem -Path 'C:\Program Files*\Microsoft Visual Studio\*\*\Common7\IDE\Remote Debugger\x64\netstandard.dll' -ErrorAction SilentlyContinue | Select-Object -First 1
if (!$facade) { throw 'Façade netstandard.dll introuvable.' }
$lines.Add('/r:"'+$facade.FullName+'"')
$lines.AddRange([string[]]@('/r:System.ComponentModel.Composition.dll','/r:System.Windows.Forms.dll','/r:System.Drawing.dll','/r:System.Net.Http.dll','/r:System.Numerics.dll','/r:System.Runtime.Serialization.dll','/r:System.IO.Compression.dll','/r:System.IO.Compression.FileSystem.dll'))
[xml]$project = [IO.File]::ReadAllText((Join-Path $source 'Pathing.csproj'))
foreach ($compile in $project.Project.ItemGroup.Compile) { if ($compile.Include) { $lines.Add('"'+(Join-Path $source $compile.Include)+'"') } }
foreach ($resource in (Get-ChildItem -LiteralPath $resources -File | Where-Object { $originalAssembly.GetManifestResourceNames() -contains $_.Name })) { $lines.Add('/resource:"'+$resource.FullName+'",'+$resource.Name) }
foreach ($name in @('CompletionDefinitions.json','PackLanguages.json','PackText.fr.json')) { $lines.Add('/resource:"'+(Join-Path $source $name)+'",'+$name) }
$rsp = Join-Path $build 'compile.rsp'
[IO.File]::WriteAllLines($rsp,$lines,(New-Object Text.UTF8Encoding($true)))
& $compiler ('@'+$rsp)
if ($LASTEXITCODE -ne 0) { throw 'Échec de compilation Pathing.' }
Copy-Item -LiteralPath (Join-Path $build 'Pathing.dll') -Destination $stage -Force
Copy-Item -LiteralPath (Join-Path $build 'Pathing.pdb') -Destination $stage -Force
$frResources = Join-Path $resources 'FrenchStrings.resources'
Write-Strings (Join-Path $source 'Strings.fr.resx') $frResources
$cultureSource = Join-Path $build 'FrenchCulture.cs'
[IO.File]::WriteAllText($cultureSource,'[assembly:System.Reflection.AssemblyCulture("fr")] [assembly:System.Reflection.AssemblyVersion("0.0.0.0")]')
$frDir = Join-Path $stage 'fr'
[IO.Directory]::CreateDirectory($frDir) | Out-Null
$frenchArgs = @('/nologo','/target:library',('/out:'+(Join-Path $frDir 'Pathing.resources.dll')),('/resource:'+$frResources+',BhModule.Community.Pathing.Strings.fr.resources'),$cultureSource)
$originalFrench = [Reflection.Assembly]::ReflectionOnlyLoad([IO.File]::ReadAllBytes((Join-Path $frDir 'Pathing.resources.dll')))
foreach ($name in $originalFrench.GetManifestResourceNames()) {
    if ($name -eq 'BhModule.Community.Pathing.Strings.fr.resources') { continue }
    $inputStream = $originalFrench.GetManifestResourceStream($name)
    $target = Join-Path $build $name
    $outputStream = [IO.File]::Create($target)
    try { $inputStream.CopyTo($outputStream) } finally { $outputStream.Dispose(); $inputStream.Dispose() }
    $frenchArgs += '/resource:'+$target+','+$name
}
& $compiler $frenchArgs
if ($LASTEXITCODE -ne 0) { throw 'Échec de compilation de la langue française.' }
$manifestPath = Join-Path $stage 'manifest.json'
$manifest = [IO.File]::ReadAllText($manifestPath) | ConvertFrom-Json
$manifest.name = 'Pathing · Français et Terminés'
$manifest | Add-Member -NotePropertyName forge_translation -NotePropertyValue @{language='fr';completionTracking=$true;baseVersion=$Version} -Force
$manifest.description = 'Édition personnelle française : menus, options et téléchargement de packs avec indication FR / US / FR-US. Classement des succès terminés conservé. Basée sur Pathing VERSION de Blish HUD.'.Replace('VERSION',$Version)
foreach ($property in $manifest.api_permissions.PSObject.Properties) { $property.Value.details = 'Permet de suivre la progression des succès et les marqueurs associés.' }
[IO.File]::WriteAllText($manifestPath,($manifest | ConvertTo-Json -Depth 20),(New-Object Text.UTF8Encoding($false)))
$manifest.version=$Version
[IO.File]::WriteAllText($manifestPath,($manifest | ConvertTo-Json -Depth 20),(New-Object Text.UTF8Encoding($false)))
$package = Join-Path $packs ('Pathing-'+$Version+'-FR-Descriptifs-Termines.bhm')
if (Test-Path -LiteralPath $package) { Remove-Item -LiteralPath $package }
[IO.Compression.ZipFile]::CreateFromDirectory($stage,$package,[IO.Compression.CompressionLevel]::Optimal,$false)
Write-Output ('Module créé : '+$package)

