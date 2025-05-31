<?php
header('Content-Type: text/plain; charset=utf-8');

// ログファイルのパス
$error_log = __DIR__ . '/error.log';
$cgi_debug_log = __DIR__ . '/cgi_debug.log';
$middleware_log = __DIR__ . '/middleware_log.txt';

// ログの内容を表示
function display_log($file, $name) {
    echo "=== $name ===\n\n";
    if (file_exists($file)) {
        echo file_get_contents($file);
    } else {
        echo "Log file does not exist: $file\n";
    }
    echo "\n\n";
}

// 各ログを表示
display_log($error_log, 'Error Log');
display_log($cgi_debug_log, 'CGI Debug Log');
display_log($middleware_log, 'Middleware Log');

// 追加の環境情報
echo "=== Environment Info ===\n\n";
echo "PHP Version: " . phpversion() . "\n";
echo "Server Software: " . $_SERVER['SERVER_SOFTWARE'] . "\n";
echo "Document Root: " . $_SERVER['DOCUMENT_ROOT'] . "\n";
echo "Script Filename: " . $_SERVER['SCRIPT_FILENAME'] . "\n";
echo "Current Working Directory: " . getcwd() . "\n";
?>