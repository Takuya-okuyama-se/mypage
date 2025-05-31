/**
 * CSRF保護のためのユーティリティ関数
 * APIリクエスト向けのトークン処理機能を提供
 */

// CSRFトークンをメタタグから取得
function getCsrfToken() {
  const metaTag = document.querySelector('meta[name="csrf-token"]');
  if (!metaTag) {
    console.error('CSRF token meta tag not found');
    return null;
  }
  return metaTag.getAttribute('content');
}

// Fetch APIを使用してCSRFトークン付きのPOSTリクエストを送信
async function fetchWithCsrf(url, data = {}, method = 'POST') {
  const token = getCsrfToken();
  if (!token) {
    throw new Error('CSRF token not available');
  }
  
  try {
    const response = await fetch(url, {
      method: method,
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': token
      },
      body: JSON.stringify(data)
    });
    
    // レスポンスがJSONでない場合のエラーハンドリング
    const contentType = response.headers.get('content-type');
    if (!contentType || !contentType.includes('application/json')) {
      if (!response.ok) {
        throw new Error(`サーバーエラー: ${response.status}`);
      }
      return { success: response.ok };
    }
    
    const result = await response.json();
    
    // 認証エラーの場合はページをリロード
    if (response.status === 401 || response.status === 403) {
      alert('セッションが期限切れか無効です。ページを更新します。');
      window.location.reload();
      return result;
    }
    
    if (!response.ok) {
      throw new Error(result.error || `API error: ${response.status}`);
    }
    
    return result;
  } catch (error) {
    console.error('API request error:', error);
    throw error;
  }
}

// AJAX (XMLHttpRequest)でのCSRFトークン設定ヘルパー
function setupAjaxCsrf() {
  if (typeof $ !== 'undefined' && $.ajax) {
    $.ajaxSetup({
      beforeSend: function(xhr, settings) {
        // POSTリクエストにCSRFトークンヘッダーを追加
        if (!/^(GET|HEAD|OPTIONS)$/i.test(settings.type)) {
          xhr.setRequestHeader('X-CSRF-Token', getCsrfToken());
        }
      }
    });
  }
}

// ページ読み込み時にセットアップを実行
document.addEventListener('DOMContentLoaded', function() {
  setupAjaxCsrf();
  console.log('CSRF protection initialized');
});
