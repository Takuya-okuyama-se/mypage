/**
 * 超直接的なメニュー修正
 * シンプルにDOM操作だけでメニューを表示させる最終手段
 */

// 即時実行関数
(function() {
  function superDirectFix() {
    console.log('🚀 超直接的なメニュー修正を実行します');
    
    // ハンバーガーボタンとメニューの取得
    const hamburgerButton = document.getElementById('nav-hamburger-toggle');
    const navLinks = document.getElementById('nav-links');
    
    // 要素がなければ終了
    if (!hamburgerButton || !navLinks) {
      console.error('❌ メニュー要素が見つかりません');
      return;
    }
    
    // メニュー開閉状態の取得・設定関数
    function getMenuState() {
      return navLinks.classList.contains('active');
    }
    
    function setMenuState(isOpen) {
      if (isOpen) {
        navLinks.classList.add('active');
        hamburgerButton.setAttribute('aria-expanded', 'true');
        document.body.classList.add('menu-open');
      } else {
        navLinks.classList.remove('active');
        hamburgerButton.setAttribute('aria-expanded', 'false');
        document.body.classList.remove('menu-open');
      }
    }
    
    // メニュー内のリンクを直接取得して表示を強制
    function forceLinksDisplay() {
      const links = navLinks.querySelectorAll('a.tab');
      console.log(`📋 メニュー内に ${links.length} 個のリンクがあります`);
      
      if (getMenuState()) {
        // メニューが開いている場合、リンクを強制表示
        links.forEach((link, index) => {
          // クローンで既存のイベントリスナーを削除
          const newLink = link.cloneNode(true);
          if (link.parentNode) {
            link.parentNode.replaceChild(newLink, link);
          }
          
          // 強制的にインラインスタイルを適用
          newLink.style.cssText = `
            display: block !important;
            visibility: visible !important;
            opacity: 1 !important;
            pointer-events: auto !important;
            z-index: 9999999 !important;
            width: 100% !important;
            padding: 15px 20px !important;
            margin: 0 !important;
            color: #333 !important;
            text-decoration: none !important;
            border-bottom: 1px solid #eee !important;
            font-weight: 500 !important;
            filter: none !important;
            -webkit-filter: none !important;
          `;
          
          // クリック時のイベント（メニューを閉じる）
          newLink.addEventListener('click', function(e) {
            if (window.innerWidth <= 768) {
              setMenuState(false);
              forceMenuStyles();
            }
          });
          
          console.log(`✅ リンク ${index+1} を強制表示: ${newLink.textContent.trim()}`);
        });
      }
    }
    
    // メニュー全体のスタイルを強制適用
    function forceMenuStyles() {
      if (getMenuState()) {
        // メニューを見えるように強制
        navLinks.style.cssText = `
          display: flex !important;
          visibility: visible !important;
          opacity: 1 !important;
          position: fixed !important;
          top: 60px !important;
          left: 0 !important;
          width: 100% !important;
          background: white !important;
          flex-direction: column !important;
          z-index: 9999999 !important;
          max-height: calc(100vh - 60px) !important;
          overflow-y: auto !important;
          box-shadow: 0 10px 30px rgba(0,0,0,0.2) !important;
          filter: none !important;
          -webkit-filter: none !important;
          pointer-events: auto !important;
        `;
        
        // オーバーレイ対応
        document.body.style.cssText += `
          overflow: hidden !important;
          position: fixed !important;
          width: 100% !important;
          height: 100% !important;
        `;
        
        // リンク表示強制
        forceLinksDisplay();
        
      } else {
        // メニューを隠す
        navLinks.style.cssText = `
          display: none !important;
          visibility: hidden !important;
          pointer-events: none !important;
        `;
        
        // ボディのスタイルをリセット
        document.body.style.overflow = '';
        document.body.style.position = '';
        document.body.style.width = '';
        document.body.style.height = '';
      }
    }
    
    // ハンバーガーボタンのイベントハンドラを再設定
    const newButton = hamburgerButton.cloneNode(true);
    hamburgerButton.parentNode.replaceChild(newButton, hamburgerButton);
    
    newButton.addEventListener('click', function(e) {
      e.preventDefault();
      e.stopPropagation();
      
      // 現在の状態を反転
      const newState = !getMenuState();
      setMenuState(newState);
      
      console.log(`🔄 メニュー状態変更: ${newState ? '開' : '閉'}`);
      
      // スタイル強制適用
      forceMenuStyles();
      
      return false;
    });
    
    // メニュー状態の監視
    const observer = new MutationObserver(function(mutations) {
      mutations.forEach(function(mutation) {
        if (mutation.attributeName === 'class') {
          forceMenuStyles();
        }
      });
    });
    
    // 監視設定
    observer.observe(navLinks, { attributes: true });
    
    // 初期状態のスタイルを適用
    forceMenuStyles();
    
    // クリックイベントをグローバルに監視
    document.addEventListener('click', function(e) {
      // 外部クリックでメニューを閉じる
      if (getMenuState() && 
          !e.target.closest('#nav-hamburger-toggle') && 
          !e.target.closest('#nav-links')) {
        setMenuState(false);
        forceMenuStyles();
      }
    });
    
    console.log('✅ 超直接的なメニュー修正が完了しました');
  }
  
  // 実行タイミングの設定
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', superDirectFix);
  } else {
    superDirectFix();
  }
  
  // 遅延実行でも確実に適用
  setTimeout(superDirectFix, 500);
  setTimeout(superDirectFix, 1500);
})();
