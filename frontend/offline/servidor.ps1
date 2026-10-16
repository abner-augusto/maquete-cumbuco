# Servidor local da maquete: serve a pasta onde está, só em 127.0.0.1. Sem dependências.
param([int]$Porta = 8137, [switch]$SemNavegador)
$raiz = $PSScriptRoot.TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
$tipos = @{ '.html'='text/html; charset=utf-8'; '.js'='text/javascript'; '.css'='text/css'; '.json'='application/json';
  '.glb'='model/gltf-binary'; '.wasm'='application/wasm'; '.webp'='image/webp'; '.jpg'='image/jpeg'; '.png'='image/png';
  '.svg'='image/svg+xml'; '.woff2'='font/woff2'; '.woff'='font/woff' }
$http = [System.Net.HttpListener]::new()
$http.Prefixes.Add("http://127.0.0.1:$Porta/")
$http.Start()
Write-Host "Maquete em http://127.0.0.1:$Porta/  (feche esta janela para parar)"
if (-not $SemNavegador) { Start-Process "http://127.0.0.1:$Porta/" }
try {
  while ($http.IsListening) {
    $ctx = $http.GetContext()
    $rel = [Uri]::UnescapeDataString($ctx.Request.Url.AbsolutePath.TrimStart('/'))
    if ($rel -eq '') { $rel = 'index.html' }
    $arquivo = [IO.Path]::GetFullPath((Join-Path $raiz $rel))
    $resp = $ctx.Response
    if (-not $arquivo.StartsWith($raiz, [StringComparison]::OrdinalIgnoreCase) -or -not (Test-Path $arquivo -PathType Leaf)) {
      $resp.StatusCode = 404
    } else {
      $bytes = [IO.File]::ReadAllBytes($arquivo)
      $ext = [IO.Path]::GetExtension($arquivo).ToLower()
      $resp.ContentType = if ($tipos.ContainsKey($ext)) { $tipos[$ext] } else { 'application/octet-stream' }
      $resp.ContentLength64 = $bytes.Length
      $resp.OutputStream.Write($bytes, 0, $bytes.Length)
    }
    $resp.Close()
  }
} finally { $http.Stop() }
