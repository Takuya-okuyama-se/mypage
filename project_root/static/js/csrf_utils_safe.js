/**
 * CSRF保護のためのユーティリティ関数（安全版）
 * エラーハンドリングを強化
 */

// CSRFトークンをメタタグから取得
function getCsrfToken() {
  try {
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    if (!metaTag) {
      console.warn('CSRF token meta tag not found');
      return null;
    }
    return metaTag.getAttribute('content');
  } catch (e) {
    console.error('Error getting CSRF token:', e);
    return null;
  }
}

// Fetch APIを使用してCSRFトークン付きのPOSTリクエストを送信
async function fetchWithCsrf(url, data = {}, method = 'POST') {
  try {
    const token = getCsrfToken();
    if (!token) {
      console.warn('CSRF token not available, proceeding without it');
    }
    
    const headers = {
      'Content-Type': 'application/json'
    };
    
    if (token) {
      headers['X-CSRF-Token'] = token;
    }
    
    const response = await fetch(url, {
      method: method,
      headers: headers,
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
  try {
    if (typeof $ !== 'undefined' && $.ajax) {
      $.ajaxSetup({
        beforeSend: function(xhr, settings) {
          // POSTリクエストにCSRFトークンヘッダーを追加
          if (!/^(GET|HEAD|OPTIONS)$/i.test(settings.type)) {
            const token = getCsrfToken();
            if (token) {
              xhr.setRequestHeader('X-CSRF-Token', token);
            }
          }
        }
      });
    }
  } catch (e) {
    console.error('Error setting up AJAX CSRF:', e);
  }
}

// ページ読み込み時にセットアップを実行
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', function() {
    setupAjaxCsrf();
    console.log('CSRF protection initialized');
  });
} else {
  // すでに読み込み済みの場合
  setupAjaxCsrf();
  console.log('CSRF protection initialized');
}