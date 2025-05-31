/**
 * モバイル向けナビゲーションメニュー制御スクリプト
 * ハンバーガーメニューの開閉と表示状態の管理を行う
 */
document.addEventListener('DOMContentLoaded', function() {
  // 要素の取得
  const hamburgerButton = document.getElementById('nav-hamburger-toggle');
  const navLinks = document.getElementById('nav-links');
  const body = document.body;
  
  // ハンバーガーボタンのクリックイベント
  if (hamburgerButton) {
    hamburgerButton.addEventListener('click', function() {
      // ナビゲーションの表示切替
      navLinks.classList.toggle('active');
      body.classList.toggle('menu-open');
      
      // アクセシビリティ属性の更新
      const isExpanded = navLinks.classList.contains('active');
      hamburgerButton.setAttribute('aria-expanded', isExpanded);
      navLinks.setAttribute('aria-hidden', !isExpanded);
      
      // 開閉状態をローカルストレージに保存
      if (window.localStorage) {
        localStorage.setItem('menuOpen', isExpanded);
      }
    });
  }
  
  // メニュー項目のクリックイベント（タップ後にメニューを閉じる）
  if (navLinks) {
    const menuItems = navLinks.querySelectorAll('a.tab');
    menuItems.forEach(function(item) {
      item.addEventListener('click', function() {
        // モバイル表示時のみ閉じる処理を実行
        if (window.innerWidth <= 768) {
          navLinks.classList.remove('active');
          body.classList.remove('menu-open');
          
          if (hamburgerButton) {
            hamburgerButton.setAttribute('aria-expanded', 'false');
          }
          navLinks.setAttribute('aria-hidden', 'true');
          
          // 開閉状態をローカルストレージに保存
          if (window.localStorage) {
            localStorage.setItem('menuOpen', false);
          }
        }
      });
    });
  }
  
  // ウィンドウリサイズ時の処理
  window.addEventListener('resize', function() {
    if (window.innerWidth > 768) {
      // デスクトップ表示の場合、メニューを常に表示
      if (navLinks) {
        navLinks.classList.remove('active');
        body.classList.remove('menu-open');
      }
    }
  });
  
  // 初期状態の設定（モバイル/デスクトップ表示の判定）
  function initializeMobileNav() {
    if (window.innerWidth <= 768) {
      // モバイル表示時の初期状態
      if (navLinks) {
        navLinks.classList.remove('active');
        navLinks.setAttribute('aria-hidden', 'true');
      }
      
      if (hamburgerButton) {
        hamburgerButton.setAttribute('aria-expanded', 'false');
      }
    } else {
      // デスクトップ表示時は常に表示
      if (navLinks) {
        navLinks.classList.remove('active');
        navLinks.setAttribute('aria-hidden', 'false');
      }
    }
  }
  
  // 初期化実行
  initializeMobileNav();
  
  // グローバルアクセス用に関数を公開
  window.initializeMobileNav = initializeMobileNav;
});
