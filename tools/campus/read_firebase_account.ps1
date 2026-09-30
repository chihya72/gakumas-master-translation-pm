[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$AccountFile,
    [switch]$Validate,
    [switch]$CopyToClipboard
)
$ErrorActionPreference = 'Stop'

function ConvertFrom-FirebaseAccountText([string]$text) {
    $candidates = [Collections.Generic.List[string]]::new()
    if ($text.TrimStart().StartsWith('<')) {
        $settings = [Xml.XmlReaderSettings]::new()
        $settings.DtdProcessing = [Xml.DtdProcessing]::Prohibit
        $settings.XmlResolver = $null
        $reader = [Xml.XmlReader]::Create([IO.StringReader]::new($text), $settings)
        $document = [Xml.XmlDocument]::new()
        $document.XmlResolver = $null
        try { $document.Load($reader) } finally { $reader.Dispose() }
        if ($document.DocumentElement.Name -ne 'map') { throw 'Expected Android SharedPreferences XML.' }
        $entries = @($document.DocumentElement.SelectNodes('string'))
        $users = @($entries | Where-Object { $_.GetAttribute('name') -eq 'com.google.firebase.auth.FIREBASE_USER' })
        if ($users.Count -gt 0) {
            foreach ($entry in $users) {
                $user = ConvertFrom-Json -InputObject $entry.InnerText -AsHashtable
                $state = ConvertFrom-Json -InputObject $user['cachedTokenState'] -AsHashtable
                if ($state['refresh_token'] -is [string]) { $candidates.Add($state['refresh_token']) }
            }
        } else {
            foreach ($entry in $entries) {
                if ($entry.GetAttribute('name').StartsWith('com.google.firebase.auth.GET_TOKEN_RESPONSE.')) {
                    $state = ConvertFrom-Json -InputObject $entry.InnerText -AsHashtable
                    if ($state['refresh_token'] -is [string]) { $candidates.Add($state['refresh_token']) }
                }
            }
        }
    } else {
        $state = ConvertFrom-Json -InputObject $text -AsHashtable
        if ($state['cachedTokenState'] -is [string]) {
            $state = ConvertFrom-Json -InputObject $state['cachedTokenState'] -AsHashtable
        }
        foreach ($name in @('refresh_token','refreshToken')) {
            # Case-sensitive: Firebase Installations' RefreshToken is unrelated.
            if (@($state.Keys | Where-Object { $_ -ceq $name }).Count -gt 0 -and $state[$name] -is [string]) {
                $candidates.Add($state[$name])
            }
        }
    }
    $tokens = @($candidates | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    if ($tokens.Count -ne 1) { throw 'Expected exactly one Firebase Auth refresh token.' }
    return $tokens[0]
}

$resolvedFile = (Resolve-Path -LiteralPath $AccountFile).Path
if ((Get-Item -LiteralPath $resolvedFile).Length -gt 1048576) { throw 'Account file exceeds 1 MiB.' }
try {
    $token = ConvertFrom-FirebaseAccountText ([IO.File]::ReadAllText($resolvedFile))
} catch {
    # Parsing errors can contain the input JSON; never print them.
    throw 'Unsupported account file, missing token, or multiple accounts. No credentials were printed.'
}
Write-Output 'One Firebase Auth refresh token found; its value is hidden.'
if ($Validate -or $CopyToClipboard) {
    $http = [Net.Http.HttpClient]::new()
    $http.Timeout = [TimeSpan]::FromSeconds(20)
    $form = [Collections.Generic.Dictionary[string,string]]::new()
    $form.Add('grant_type','refresh_token')
    $form.Add('refresh_token',$token)
    $content = [Net.Http.FormUrlEncodedContent]::new($form)
    $response = $null
    try {
        $http.DefaultRequestHeaders.Add('X-Android-Package','com.bandainamcoent.idolmaster_gakuen')
        $http.DefaultRequestHeaders.Add('X-Android-Cert','D05C4DC398804FEB2ADF30E8854500D2834EAFED')
        $endpoint = 'https://securetoken.googleapis.com/v1/token?key=AIzaSyCe_vKRW5Pc0rTXFksur-ZCDb_kRCxNhng'
        $response = $http.PostAsync($endpoint,$content).GetAwaiter().GetResult()
        if (-not $response.IsSuccessStatusCode) {
            throw ('Firebase rejected the credential; HTTP ' + [int]$response.StatusCode + '.')
        }
        $result = ConvertFrom-Json -InputObject ($response.Content.ReadAsStringAsync().GetAwaiter().GetResult()) -AsHashtable
        if ([string]$result['project_id'] -ne '544792984478' -or [string]::IsNullOrWhiteSpace($result['id_token']) -or [string]::IsNullOrWhiteSpace($result['refresh_token'])) {
            throw 'The response is not a valid token for the campus game project.'
        }
        $token = $result['refresh_token']
        Write-Output 'Firebase validation passed for the campus game project.'
    } catch {
        throw 'Firebase validation failed. No credentials or response bodies were printed.'
    } finally {
        if ($response) { $response.Dispose() }
        $content.Dispose()
        $http.Dispose()
        $form.Clear()
        $result = $null
    }
}
if ($CopyToClipboard) {
    Set-Clipboard -Value $token
    Write-Output 'Validated refresh token copied to clipboard for CAMPUS_REFRESH_TOKEN.'
}
$token = $null
