/**
 * 統一ハンバーガーメニュー実装 - 修正版
 * 2025年5月29日更新
 */
(function() {
  'use strict';
  
  // DOMが準備できてから実行
  document.addEventListener('DOMContentLoaded', initHamburgerMenu);
  
  /**
   * ハンバーガーメニューの初期化
   */
  function initHamburgerMenu() {
    console.log('🍔 ハンバーガーメニューを初期化中...');
    
    // 要素を取得
    const hamburgerButton = document.getElementById('nav-hamburger-toggle');
    const navLinks = document.getElementById('nav-links');
    const body = document.body;
    
    // 要素がない場合は終了
    if (!hamburgerButton || !navLinks) {
      console.error('❌ ハンバーガーボタンまたはナビリンクが見つかりません');
      return;
    }
    
    // ボタンを強制的に表示状態にする（モバイル表示時）
    if (window.innerWidth <= 768) {
      hamburgerButton.style.display = 'flex';
      hamburgerButton.style.visibility = 'visible';
      hamburgerButton.style.opacity = '1';
      hamburgerButton.style.pointerEvents = 'auto';
    }
    
    // ハンバーガーボタンのクリックイベント
    hamburgerButton.addEventListener('click', function(e) {
      e.preventDefault();
      e.stopPropagation();
      
      const isExpanded = hamburgerButton.getAttribute('aria-expanded') === 'true';
      
      if (isExpanded) {
        // メニューを閉じる
        closeMenu();
      } else {
        // メニューを開く
        openMenu();
      }
    });
    
    // メニュー項目のクリック時にモバイルでは自動的にメニューを閉じる
    const menuItems = navLinks.querySelectorAll('a.tab');
    menuItems.forEach(function(item) {
      item.addEventListener('click', function() {
        // モバイル表示時のみ閉じる処理を実行
        if (window.innerWidth <= 768) {
          closeMenu();
        }
      });
    });
    
    // 外部クリックでメニューを閉じる
    document.addEventListener('click', function(e) {
      if (window.innerWidth <= 768 && 
          !hamburgerButton.contains(e.target) && 
          !navLinks.contains(e.target) &&
          navLinks.classList.contains('active')) {
        closeMenu();
      }
    });
    
    // ESCキーでメニューを閉じる
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && navLinks.classList.contains('active')) {
        closeMenu();
      }
    });
    
    // ウィンドウリサイズ時の処理
    window.addEventListener('resize', function() {
      if (window.innerWidth > 768) {
        closeMenu();
      }
    });
    
    /**
     * メニューを開く関数
     */
    function openMenu() {
      // メニューを表示
      navLinks.classList.add('active');
      hamburgerButton.classList.add('active');
      hamburgerButton.setAttribute('aria-expanded', 'true');
      hamburgerButton.setAttribute('aria-label', 'メニューを閉じる');
      navLinks.setAttribute('aria-hidden', 'false');
      body.classList.add('menu-open');
    }
    
    /**
     * メニューを閉じる関数
     */
    function closeMenu() {
      // メニューを非表示
      navLinks.classList.remove('active');
      hamburgerButton.classList.remove('active');
      hamburgerButton.setAttribute('aria-expanded', 'false');
      hamburgerButton.setAttribute('aria-label', 'メニューを開く');
      navLinks.setAttribute('aria-hidden', 'true');
      
      // スクロール位置を復元
      if (body.classList.contains('menu-open')) {
        const scrollY = parseInt(body.dataset.scrollY || '0');
        body.style.position = '';
        body.style.top = '';
        body.style.width = '';
        window.scrollTo(0, scrollY);
      }
      
      body.classList.remove('menu-open');
    }
    
    console.log('✅ ハンバーガーメニューの初期化完了');
  }
})();
