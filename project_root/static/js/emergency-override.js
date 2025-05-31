/**
 * 緊急オーバーライドスクリプト
 * どうしてもハンバーガーメニューが表示されない場合の最終手段
 */
(function() {
  console.log('⚡ 緊急オーバーライドスクリプトを実行します');
  
  // この関数を呼び出すとメニューが強制表示される
  function emergencyMenuFix() {
    // メニュー要素を取得
    const navLinks = document.getElementById('nav-links');
    if (!navLinks) return;
    
    // メニューボタンを取得
    const hamburgerButton = document.getElementById('nav-hamburger-toggle');
    if (!hamburgerButton) return;
    
    console.log('⚡ 緊急修正：メニューを強制置換します');
    
    // 既存のメニューを非表示
    navLinks.style.display = 'none';
    
    // 新しいメニューコンテナを作成
    const newMenuContainer = document.createElement('div');
    newMenuContainer.id = 'emergency-menu-container';
    newMenuContainer.style.cssText = `
      display: none;
      position: fixed;
      top: 60px;
      left: 0;
      width: 100%;
      background-color: white;
      box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
      z-index: 100000;
      flex-direction: column;
      max-height: calc(100vh - 60px);
      overflow-y: auto;
    `;
    
    // 元のメニューリンクをコピー
    const originalLinks = navLinks.querySelectorAll('a.tab');
    originalLinks.forEach(link => {
      const newLink = document.createElement('a');
      newLink.href = link.href;
      newLink.className = link.className;
      newLink.textContent = link.textContent;
      newLink.style.cssText = `
        display: block;
        padding: 15px;
        text-decoration: none;
        color: #333;
        border-bottom: 1px solid #eee;
        width: 100%;
      `;
      
      // アイコンがあれば復元
      const icon = link.querySelector('i');
      if (icon) {
        const newIcon = document.createElement('i');
        newIcon.className = icon.className;
        newIcon.style.marginRight = '10px';
        newLink.prepend(newIcon);
      }
      
      // イベントハンドラもコピー
      newLink.addEventListener('click', function(e) {
        // 通常のリンクと同じ動作をさせる
        if (this.href) {
          window.location.href = this.href;
          e.preventDefault(); 
        }
        
        // メニューを閉じる
        newMenuContainer.style.display = 'none';
        document.body.classList.remove('menu-open');
        
        // オーバーレイ非表示
        const overlay = document.querySelector('#emergency-overlay');
        if (overlay) {
          overlay.style.display = 'none';
        }
      });
      
      newMenuContainer.appendChild(newLink);
    });
    
    // オーバーレイ作成
    const overlay = document.createElement('div');
    overlay.id = 'emergency-overlay';
    overlay.style.cssText = `
      display: none;
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background-color: rgba(0, 0, 0, 0.7);
      z-index: 99999;
    `;
    
    // オーバーレイのクリックイベント
    overlay.addEventListener('click', function() {
      newMenuContainer.style.display = 'none';
      overlay.style.display = 'none';
      document.body.classList.remove('menu-open');
    });
    
    // ハンバーガーボタンのイベント置き換え
    const newButton = hamburgerButton.cloneNode(true);
    newButton.addEventListener('click', function(e) {
      e.preventDefault();
      e.stopPropagation();
      
      const isVisible = newMenuContainer.style.display === 'flex';
      
      if (isVisible) {
        // メニューを閉じる
        newMenuContainer.style.display = 'none';
        overlay.style.display = 'none';
        document.body.classList.remove('menu-open');
      } else {
        // メニューを開く
        newMenuContainer.style.display = 'flex';
        overlay.style.display = 'block';
        document.body.classList.add('menu-open');
      }
    });
    
    // 元のボタンと置き換え
    hamburgerButton.parentNode.replaceChild(newButton, hamburgerButton);
    
    // 新要素をDOMに追加
    document.body.appendChild(overlay);
    document.body.appendChild(newMenuContainer);
    
    // 元のメニューのイベントリスナーを無効化
    const oldClone = navLinks.cloneNode(true);
    navLinks.parentNode.replaceChild(oldClone, navLinks);
    
    console.log('⚡ 緊急メニュー修正完了');
  }
  
  // ボタンがクリックされた時にメニューを10回チェック
  function checkAndFixIfNeeded() {
    let checkCount = 0;
    let menuFixed = false;
    
    document.addEventListener('click', function(e) {
      // ハンバーガーボタンかどうかを確認
      if (e.target.id === 'nav-hamburger-toggle' || 
          e.target.closest('#nav-hamburger-toggle')) {
        
        if (menuFixed) return;
        checkCount++;
        
        // まだ修正していない場合、メニューが表示されるか確認
        setTimeout(() => {
          const navLinks = document.getElementById('nav-links');
          if (navLinks) {
            const isVisible = (getComputedStyle(navLinks).display !== 'none' && 
                              getComputedStyle(navLinks).visibility !== 'hidden');
            
            const menuItems = navLinks.querySelectorAll('a.tab');
            const anyLinkVisible = Array.from(menuItems).some(item => 
              getComputedStyle(item).display !== 'none' && 
              getComputedStyle(item).visibility !== 'hidden');
            
            console.log(`⚡ メニューチェック #${checkCount}: メニュー表示=${isVisible}, リンク表示=${anyLinkVisible}`);
            
            // メニュー自体は表示されているが、リンクが表示されていない場合
            if (isVisible && !anyLinkVisible && checkCount >= 3) {
              console.log('⚡ 多重チェック後にメニュー項目が表示されていない状態を検出');
              emergencyMenuFix();
              menuFixed = true;
            } 
            // 3回以上クリックしてもメニューが表示されない場合
            else if (!isVisible && checkCount >= 5) {
              console.log('⚡ 5回のクリック後もメニューが表示されない状態を検出');
              emergencyMenuFix();
              menuFixed = true;
            }
          }
        }, 300);
      }
    }, true);
  }
  
  // DOMが読み込まれた後に実行
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', checkAndFixIfNeeded);
  } else {
    checkAndFixIfNeeded();
  }
})();
