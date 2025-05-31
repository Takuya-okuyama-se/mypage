/**
 * 統一ハンバーガーメニュー実装
 * すべての競合するスクリプトを置き換える単一の実装
 * 2025年5月22日作成
 */
(function() {
  'use strict';
  
  // 設定
  const CONFIG = {
    MOBILE_BREAKPOINT: 768,
    TRANSITION_DURATION: 300,
    Z_INDEX: {
      OVERLAY: 9999998,
      MENU: 9999999,
      BUTTON: 10000000
    }
  };
  
  // グローバル変数
  let isMenuOpen = false;
  let hamburgerButton = null;
  let navLinks = null;
  let menuOverlay = null;
  
  /**
   * 初期化関数
   */
  function initHamburgerMenu() {
    console.log('🍔 統一ハンバーガーメニューを初期化中...');
    
    // 既存の競合するスクリプトを無効化
    disableConflictingScripts();
    
    // DOM要素を取得
    if (!getDOMElements()) {
      console.error('❌ 必要なDOM要素が見つかりません');
      return;
    }
    
    // 初期設定
    setupInitialState();
    
    // オーバーレイ作成
    createMenuOverlay();
    
    // イベントリスナー設定
    setupEventListeners();
    
    // レスポンシブ対応
    setupResponsiveHandling();
    
    console.log('✅ 統一ハンバーガーメニューの初期化完了');
  }
  
  /**
   * 競合するスクリプトを無効化
   */
  function disableConflictingScripts() {
    // 既存のイベントリスナーをクリア
    const existingButtons = document.querySelectorAll('#nav-hamburger-toggle, .hamburger-button');
    existingButtons.forEach(btn => {
      const newBtn = btn.cloneNode(true);
      if (btn.parentNode) {
        btn.parentNode.replaceChild(newBtn, btn);
      }
    });
    
    // 既存のオーバーレイを削除
    const existingOverlays = document.querySelectorAll('.menu-overlay, #production-menu-overlay, #emergency-overlay');
    existingOverlays.forEach(overlay => overlay.remove());
    
    // 既存のメニューコンテナを削除
    const existingContainers = document.querySelectorAll('#production-menu-container, #mobile-menu');
    existingContainers.forEach(container => container.remove());
  }
  
  /**
   * DOM要素を取得
   */
  function getDOMElements() {
    hamburgerButton = document.getElementById('nav-hamburger-toggle');
    navLinks = document.getElementById('nav-links');
    
    if (!hamburgerButton || !navLinks) {
      console.error('❌ ハンバーガーボタンまたはナビリンクが見つかりません');
      return false;
    }
    
    console.log('✅ DOM要素を取得しました');
    return true;
  }
  
  /**
   * 初期状態を設定
   */
  function setupInitialState() {
    // ボタンの初期状態
    hamburgerButton.setAttribute('aria-expanded', 'false');
    hamburgerButton.setAttribute('aria-label', 'メニューを開く');
    hamburgerButton.classList.remove('active');
    
    // メニューの初期状態
    navLinks.setAttribute('aria-hidden', 'true');
    navLinks.classList.remove('active');
    
    // ボディクラスをクリア
    document.body.classList.remove('menu-open');
    
    // メニューが閉じた状態に設定
    isMenuOpen = false;
    
    // ボタンの表示を確保
    hamburgerButton.style.setProperty('display', 'block', 'important');
    hamburgerButton.style.setProperty('visibility', 'visible', 'important');
    hamburgerButton.style.setProperty('opacity', '1', 'important');
    
    console.log('✅ 初期状態を設定しました');
  }
  
  /**
   * メニューオーバーレイを作成
   */
  function createMenuOverlay() {
    menuOverlay = document.createElement('div');
    menuOverlay.className = 'unified-menu-overlay';
    menuOverlay.style.cssText = `
      position: fixed !important;
      top: 0 !important;
      left: 0 !important;
      width: 100% !important;
      height: 100vh !important;
      background-color: rgba(0, 0, 0, 0.5) !important;
      z-index: ${CONFIG.Z_INDEX.OVERLAY} !important;
      display: none !important;
      opacity: 0 !important;
      visibility: hidden !important;
      transition: opacity ${CONFIG.TRANSITION_DURATION}ms ease !important;
      pointer-events: none !important;
    `;
    
    document.body.appendChild(menuOverlay);
    console.log('✅ メニューオーバーレイを作成しました');
  }
  
  /**
   * イベントリスナーを設定
   */
  function setupEventListeners() {
    // ハンバーガーボタンのクリック
    hamburgerButton.addEventListener('click', handleButtonClick);
    
    // タッチデバイス対応
    hamburgerButton.addEventListener('touchend', handleButtonClick, { passive: false });
    
    // キーボード対応
    hamburgerButton.addEventListener('keydown', handleKeydown);
    
    // オーバーレイクリックでメニューを閉じる
    menuOverlay.addEventListener('click', closeMenu);
    
    // メニュー項目クリック時にメニューを閉じる
    const menuItems = navLinks.querySelectorAll('a.tab, a[href]');
    menuItems.forEach(item => {
      item.addEventListener('click', handleMenuItemClick);
    });
    
    // ESCキーでメニューを閉じる
    document.addEventListener('keydown', handleEscapeKey);
    
    console.log('✅ イベントリスナーを設定しました');
  }
  
  /**
   * レスポンシブ対応を設定
   */
  function setupResponsiveHandling() {
    // ウィンドウリサイズ時の処理
    let resizeTimeout;
    window.addEventListener('resize', () => {
      clearTimeout(resizeTimeout);
      resizeTimeout = setTimeout(() => {
        if (window.innerWidth > CONFIG.MOBILE_BREAKPOINT && isMenuOpen) {
          closeMenu();
        }
      }, 100);
    });
    
    // ページ遷移前にメニューを閉じる
    window.addEventListener('beforeunload', closeMenu);
    
    // 履歴操作時にメニューを閉じる
    window.addEventListener('popstate', closeMenu);
  }
  
  /**
   * ボタンクリックハンドラー
   */
  function handleButtonClick(e) {
    e.preventDefault();
    e.stopPropagation();
    
    console.log('🖱️ ハンバーガーボタンがクリックされました');
    
    if (isMenuOpen) {
      closeMenu();
    } else {
      openMenu();
    }
  }
  
  /**
   * キーボードハンドラー
   */
  function handleKeydown(e) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleButtonClick(e);
    }
  }
  
  /**
   * メニュー項目クリックハンドラー
   */
  function handleMenuItemClick() {
    if (window.innerWidth <= CONFIG.MOBILE_BREAKPOINT && isMenuOpen) {
      // 少し遅延させてページ遷移を確実にする
      setTimeout(closeMenu, 100);
    }
  }
  
  /**
   * ESCキーハンドラー
   */
  function handleEscapeKey(e) {
    if (e.key === 'Escape' && isMenuOpen) {
      closeMenu();
    }
  }
  
  /**
   * メニューを開く
   */
  function openMenu() {
    if (isMenuOpen) return;
    
    console.log('📖 メニューを開きます');
    
    // 状態を更新
    isMenuOpen = true;
    
    // ボタンの状態を更新
    hamburgerButton.classList.add('active');
    hamburgerButton.setAttribute('aria-expanded', 'true');
    hamburgerButton.setAttribute('aria-label', 'メニューを閉じる');
    
    // メニューの状態を更新
    navLinks.classList.add('active');
    navLinks.setAttribute('aria-hidden', 'false');
    
    // ボディクラスを追加
    document.body.classList.add('menu-open');
    
    // オーバーレイを表示
    menuOverlay.style.setProperty('display', 'block', 'important');
    menuOverlay.style.setProperty('pointer-events', 'auto', 'important');
    
    // アニメーション用の少し遅延
    requestAnimationFrame(() => {
      menuOverlay.style.setProperty('opacity', '1', 'important');
      menuOverlay.style.setProperty('visibility', 'visible', 'important');
    });
    
    // メニューを強制表示
    navLinks.style.setProperty('display', 'flex', 'important');
    navLinks.style.setProperty('visibility', 'visible', 'important');
    navLinks.style.setProperty('opacity', '1', 'important');
    navLinks.style.setProperty('z-index', CONFIG.Z_INDEX.MENU.toString(), 'important');
    
    console.log('✅ メニューが開かれました');
  }
  
  /**
   * メニューを閉じる
   */
  function closeMenu() {
    if (!isMenuOpen) return;
    
    console.log('📕 メニューを閉じます');
    
    // 状態を更新
    isMenuOpen = false;
    
    // ボタンの状態を更新
    hamburgerButton.classList.remove('active');
    hamburgerButton.setAttribute('aria-expanded', 'false');
    hamburgerButton.setAttribute('aria-label', 'メニューを開く');
    
    // メニューの状態を更新
    navLinks.classList.remove('active');
    navLinks.setAttribute('aria-hidden', 'true');
    
    // ボディクラスを削除
    document.body.classList.remove('menu-open');
    
    // オーバーレイを非表示
    menuOverlay.style.setProperty('opacity', '0', 'important');
    menuOverlay.style.setProperty('visibility', 'hidden', 'important');
    menuOverlay.style.setProperty('pointer-events', 'none', 'important');
    
    // アニメーション終了後にdisplay:noneを設定
    setTimeout(() => {
      menuOverlay.style.setProperty('display', 'none', 'important');
    }, CONFIG.TRANSITION_DURATION);
    
    console.log('✅ メニューが閉じられました');
  }
  
  /**
   * 初期化実行
   */
  function bootstrap() {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', initHamburgerMenu);
    } else {
      initHamburgerMenu();
    }
    
    // バックアップとして遅延実行
    setTimeout(initHamburgerMenu, 100);
  }
  
  // 実行
  bootstrap();
  
  console.log('🚀 統一ハンバーガーメニュースクリプト読み込み完了');
  
})();
