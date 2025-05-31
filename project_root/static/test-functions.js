// テスト用スクリプト - ブラウザコンソールでの動作確認
console.log('テストスクリプト開始');

// 修正後の関数が利用可能かチェック
function checkFunctions() {
    const functionsToCheck = [
        'selectStage',
        'switchTab', 
        'playAllVocabulary',
        'calculateScore',
        'nextStage',
        'showVocabularyModal'
    ];
    
    functionsToCheck.forEach(funcName => {
        if (typeof window[funcName] === 'function') {
            console.log(`✓ ${funcName} は利用可能`);
        } else {
            console.error(`✗ ${funcName} は未定義`);
        }
    });
}

// DOM読み込み後にチェック実行
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', checkFunctions);
} else {
    checkFunctions();
}

// 手動でテストできるような関数も追加
window.testFunctions = checkFunctions;
