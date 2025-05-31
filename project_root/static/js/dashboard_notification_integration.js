// dashboard_notification_integration.js
// ダッシュボードに成績・内申向上通知のバッジを表示するスクリプト

document.addEventListener('DOMContentLoaded', function() {    // CSRFトークンを取得
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';
    
    // 成績・内申向上通知の件数を取得する関数
    function fetchImprovementNotificationCount() {
      fetch('/myapp/index.cgi/api/teacher/improvement-notification-count', {
        headers: {
          'X-CSRF-Token': csrfToken
        }
      })
        .then(response => response.json())
        .then(data => {
          // ダッシュボードのバッジを更新
          updateNotificationBadges(data);
          
          // 通知センターを更新（存在する場合）
          updateNotificationCenter(data);
        })
        .catch(error => console.error('Error fetching notification count:', error));
    }
    
    // 通知バッジを更新する関数
    function updateNotificationBadges(data) {
      // ダッシュボードのクイックリンク内のバッジ
      const improvementBadge = document.getElementById('improvement-notification-badge');
      if (improvementBadge) {
        improvementBadge.textContent = data.total_count;
        
        // 件数によってバッジの表示/非表示を切り替え
        if (data.total_count > 0) {
          improvementBadge.style.display = 'inline-block';
        } else {
          improvementBadge.style.display = 'none';
        }
      }
      
      // 通知サマリーボックス内のバッジ
      const summaryBadge = document.getElementById('improvement-summary-badge');
      if (summaryBadge) {
        summaryBadge.textContent = data.total_count;
        
        if (data.total_count > 0) {
          summaryBadge.style.display = 'inline-block';
        } else {
          summaryBadge.style.display = 'none';
        }
      }
    }
    
  // 通知センターを更新する関数
function updateNotificationCenter(data) {
    // 通知センターがなければ作成する
    let notificationCenter = document.getElementById('notification-center');
    if (!notificationCenter) {
      notificationCenter = document.createElement('div');
      notificationCenter.id = 'notification-center';
      document.body.appendChild(notificationCenter);
        // CSSが読み込まれていなければ読み込む
      if (!document.querySelector('link[href*="notification-center.css"]')) {
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = '/myapp/index.cgi/static/notification-center.css'; // 正しいパスに修正
        document.head.appendChild(link);
      }
    }
      // トグルボタンがなければ作成（毎回確認して作成）
    let notifyBtn = document.getElementById('notification-toggle-btn');
    if (!notifyBtn) {
      notifyBtn = document.createElement('button');
      notifyBtn.id = 'notification-toggle-btn';
      notifyBtn.innerHTML = '<i class="fas fa-bell"></i><span class="badge">0</span>';
      notifyBtn.addEventListener('click', function(event) {
        toggleNotificationCenter(event);
      });
      document.body.appendChild(notifyBtn);
    }
      // 通知バッジ更新
    const currentBtn = document.getElementById('notification-toggle-btn');
    if (currentBtn) {
      const badge = currentBtn.querySelector('.badge');
      if (badge) {
        badge.textContent = data.total_count;
        badge.style.display = data.total_count > 0 ? 'block' : 'none';
      }
    }
    
    // 通知センターの内容を更新
    if (data.total_count > 0) {
      // 通知がある場合は詳細を表示
      let notificationItems = '';
      
      if (data.elementary_count > 0) {
        notificationItems += `
          <div class="notification-item">
            <span class="notification-icon elementary">📈</span>
            <span class="notification-text">小学生の成績向上通知: ${data.elementary_count}件</span>
          </div>
        `;
      }
      
      if (data.middle_count > 0) {
        notificationItems += `
          <div class="notification-item">
            <span class="notification-icon middle">📊</span>
            <span class="notification-text">中学生の内申点向上通知: ${data.middle_count}件</span>
          </div>
        `;
      }
      
      if (data.high_count > 0) {
        notificationItems += `
          <div class="notification-item">
            <span class="notification-icon high">📝</span>
            <span class="notification-text">高校生の成績向上通知: ${data.high_count}件</span>
          </div>
        `;
      }
      
      notificationCenter.innerHTML = `
        <div class="notification-header">
          <h5>成績・内申向上通知 <span class="notification-count">${data.total_count}</span></h5>
          <button class="close-btn" onclick="document.getElementById('notification-center').style.display='none';">×</button>
        </div>
        <div class="notification-body">
          ${notificationItems}
        </div>
        <div class="notification-footer">
          <a href="/myapp/index.cgi/teacher/improvement-notifications" class="notification-link">
            すべての通知を確認する
          </a>
        </div>
      `;
    } else {
      // 通知がない場合はメッセージを表示
      notificationCenter.innerHTML = `
        <div class="notification-header">
          <h5>通知</h5>
          <button class="close-btn" onclick="document.getElementById('notification-center').style.display='none';">×</button>
        </div>
        <div class="notification-body">
          <div class="notification-item">
            <span class="notification-text">新しい通知はありません</span>
          </div>
        </div>
      `;
    }
  }
  // 通知センターの表示/非表示を切り替える関数
  function toggleNotificationCenter(event) {
    // イベントがあればデフォルトの動作を抑制
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }
    
    const notificationCenter = document.getElementById('notification-center');
    if (notificationCenter) {
      // 通知センターが表示されているか確認（CSSのdisplayプロパティを直接見る）
      const isVisible = window.getComputedStyle(notificationCenter).display !== 'none';
      
      if (isVisible) {
        notificationCenter.style.display = 'none';
        
        // オーバーレイを削除
        const overlay = document.getElementById('notification-overlay');
        if (overlay) {
          document.body.removeChild(overlay);
        }
      } else {
        // オーバーレイを作成
        let overlay = document.getElementById('notification-overlay');
        if (!overlay) {
          overlay = document.createElement('div');
          overlay.id = 'notification-overlay';
          overlay.style.position = 'fixed';
          overlay.style.top = '0';
          overlay.style.left = '0';
          overlay.style.width = '100%';
          overlay.style.height = '100%';
          overlay.style.backgroundColor = 'rgba(0,0,0,0.3)';
          overlay.style.zIndex = '9990';
          overlay.addEventListener('click', function() {
            notificationCenter.style.display = 'none';
            document.body.removeChild(this);
          });
          document.body.appendChild(overlay);
        }
        
        notificationCenter.style.display = 'block';
        notificationCenter.style.zIndex = '9999'; // オーバーレイの上に表示
      }
    }
  }// 初期化処理
    function init() {
      // FontAwesomeが読み込まれていない場合は読み込む
      if (!document.querySelector('link[href*="font-awesome"]')) {
        const faLink = document.createElement('link');
        faLink.rel = 'stylesheet';
        faLink.href = 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css';
        document.head.appendChild(faLink);
      }
      
      // 遅延させて既存のメニュー構造が読み込まれた後に実行
      setTimeout(function() {
        // 通知数を取得
        fetchImprovementNotificationCount();
        
        // 30秒ごとに更新
        setInterval(fetchImprovementNotificationCount, 30000);
      }, 500);
    }
      
    // 講師ダッシュボードの場合のみ初期化
    if (document.querySelector('.teacher-dashboard')) {
      init();
    } else {
      // テスト用: 画面が塾生徒サイトの場合も初期化
      if (document.querySelector('塾生徒サイト') || document.title.includes('塾生徒')) {
        init();
      }
    }
});