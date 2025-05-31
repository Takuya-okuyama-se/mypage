/**
 * メニューオーバーレイ制御スクリプト
 * メニューの前面表示を補助
 */
(function() {
  // DOMの読み込み完了時に実行
  function setupOverlay() {
    console.log('🔍 メニューオーバーレイを設定します');
    
    // 要素取得
    const hamburgerButton = document.getElementById('nav-hamburger-toggle');
    const navLinks = document.getElementById('nav-links');
    const body = document.body;
    const html = document.documentElement;
    
    // 要素がない場合は終了
    if (!hamburgerButton || !navLinks) {
      console.error('❌ メニュー要素が見つかりません');
      return;
    }
    
    // オーバーレイ要素を作成
    let overlay = document.querySelector('.menu-overlay');
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.className = 'menu-overlay';
      document.body.appendChild(overlay);
      
      // オーバーレイクリック時にメニューを閉じる
      overlay.addEventListener('click', function() {
        // メニューが開いていれば閉じる
        if (navLinks.classList.contains('active')) {
          navLinks.classList.remove('active');
          hamburgerButton.setAttribute('aria-expanded', 'false');
          body.classList.remove('menu-open');
          html.classList.remove('scroll-locked');
        }
      });
    }
    
    // メニュー状態監視 (Mutation Observer)
    const observer = new MutationObserver(function(mutations) {
      mutations.forEach(function(mutation) {
        if (mutation.target === body && mutation.attributeName === 'class') {
          // メニュー開閉状態に応じてHTMLタグのクラスも更新
          if (body.classList.contains('menu-open')) {
            html.classList.add('scroll-locked');
          } else {
            html.classList.remove('scroll-locked');
          }
        } else if (mutation.target === navLinks && mutation.attributeName === 'class') {
          // メニュークラスが変更された場合、状態を確認
          if (navLinks.classList.contains('active')) {
            // メニューが開いた
            body.classList.add('menu-open');
            html.classList.add('scroll-locked');
          } else {
            // メニューが閉じた
            body.classList.remove('menu-open');
            html.classList.remove('scroll-locked');
          }
        }
      });
    });
    
    // 監視対象と設定
    observer.observe(body, { attributes: true });
    observer.observe(navLinks, { attributes: true });
    
    console.log('✅ メニューオーバーレイ設定が完了しました');
  }
  
  // ページ読み込み完了時に実行
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupOverlay);
  } else {
    setupOverlay();
  }
  
  // バックアップ: 遅延実行
  setTimeout(setupOverlay, 1000);
})();
