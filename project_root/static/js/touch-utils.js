/**
 * タッチデバイス向けの最適化ユーティリティ
 * モバイルデバイス、特にiOSでの操作性を向上させる
 */

// タッチデバイスを検出
const isTouchDevice = () => {
  return ('ontouchstart' in window) || 
         (navigator.maxTouchPoints > 0) ||
         (navigator.msMaxTouchPoints > 0);
};

// モバイルデバイスかどうかを検出
const isMobileDevice = () => {
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
};

// iOS固有のデバイスを検出
const isIOSDevice = () => {
  return /iPad|iPhone|iPod/.test(navigator.userAgent) || 
         (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
};

// タッチ要素にクリック遅延を解消するための設定を適用
function applyTouchOptimization(element) {
  if (!element) return;
  
  // iOS Safariの300ms遅延対策
  element.style.touchAction = 'manipulation';
  element.style.webkitTapHighlightColor = 'transparent';
  
  // タップハイライト無効化
  element.addEventListener('touchstart', function(e) {
    this.classList.add('touch-active');
  }, { passive: true });
  
  element.addEventListener('touchend', function(e) {
    this.classList.remove('touch-active');
  }, { passive: true });
  
  // スクロールを妨げないように
  element.addEventListener('touchmove', function(e) {
    this.classList.remove('touch-active');
  }, { passive: true });
}

// 複数要素に一括適用
function optimizeTouchElements(selector) {
  const elements = document.querySelectorAll(selector);
  elements.forEach(element => {
    applyTouchOptimization(element);
  });
}

// エクスポート
window.TouchUtils = {
  isTouchDevice,
  isMobileDevice,
  isIOSDevice,
  applyTouchOptimization,
  optimizeTouchElements
};
