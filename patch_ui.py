import os
import re

BASE_DIR = r"C:\Users\Administrator\AppData\Local\hermes\workspace\web-scrcpy-fresh"
INDEX_HTML = os.path.join(BASE_DIR, "templates", "index.html")
MAIN_JS = os.path.join(BASE_DIR, "static", "js", "input.js")

def patch_index_html():
    with open(INDEX_HTML, "r", encoding="utf-8") as f:
        content = f.read()

    # Change body layout to row
    content = re.sub(
        r'body\{margin:0;height:100dvh;display:flex;flex-direction:column;color:var\(--txt\);overflow:hidden\}',
        r'body{margin:0;height:100dvh;display:flex;flex-direction:row;color:var(--txt);overflow:hidden;background:#05070e}',
        content
    )

    # Convert .top and .toolbar into a sidebar layout
    content = re.sub(
        r'(<body>)',
        r'\1\n  <div class="sidebar" style="width:280px; flex-shrink:0; display:flex; flex-direction:column; background:rgba(10,12,26,0.65); border-right:1px solid var(--line); backdrop-filter:blur(20px); -webkit-backdrop-filter:blur(20px); z-index:10; box-shadow: 5px 0 25px rgba(0,0,0,0.5); overflow-y:auto; overflow-x:hidden;">\n    <div class="sidebar-inner" style="padding: 16px; display:flex; flex-direction:column; gap:16px;">',
        content
    )

    content = content.replace(
        '<div class="video-wrap" id="videoWrap">',
        '    </div>\n  </div> <!-- sidebar -->\n  <div class="main-content" style="flex:1; position:relative; display:flex; flex-direction:column;">\n    <div class="video-wrap" id="videoWrap">'
    )

    content = content.replace('</body>', '  </div>\n</body>')

    drag_drop_html = '''
    <div id="dropZone" style="position:absolute; inset:0; z-index:100; background:rgba(16, 185, 129, 0.2); backdrop-filter:blur(4px); display:none; align-items:center; justify-content:center; flex-direction:column; color:#fff; border: 4px dashed #10b981; border-radius: 20px; margin: 20px; pointer-events:none;">
      <i class="fa-solid fa-cloud-arrow-up" style="font-size:4rem; margin-bottom:16px; color:#34d399"></i>
      <h2 style="font-family:sans-serif; margin:0">Thả file để Push / Cài đặt APK</h2>
    </div>
    '''
    content = content.replace('<div class="video-wrap" id="videoWrap">', drag_drop_html + '\n    <div class="video-wrap" id="videoWrap">')

    keymap_html = '''
    <div id="keymapOverlay" style="position:absolute; inset:0; z-index:90; display:none; pointer-events:auto;">
       <div style="position:absolute; top: 10px; left: 50%; transform: translateX(-50%); background:rgba(0,0,0,0.8); color:#fbbf24; padding:8px 16px; border-radius:20px; font-family:sans-serif; font-size:0.85rem; font-weight:bold; border:1px solid #fbbf24; box-shadow:0 4px 12px rgba(0,0,0,0.5);">
         <i class="fa-solid fa-pen-ruler"></i> CHẾ ĐỘ GÁN PHÍM: Click vào màn hình để thêm phím. Bấm "Gán phím" lần nữa để lưu.
       </div>
    </div>
    '''
    content = content.replace('<div class="phone-mockup" id="phoneMockup">', '<div class="phone-mockup" id="phoneMockup">\n      ' + keymap_html)

    content = re.sub(
        r'\.top\{[^}]+\}',
        r'.top{display:flex;flex-direction:column;gap:12px;}',
        content
    )
    content = re.sub(r'\.top::after\{[^}]+\}', '', content)

    content = re.sub(
        r'\.toolbar\{[^}]+\}',
        r'.toolbar{display:grid; grid-template-columns: repeat(4, 1fr); gap:10px;}',
        content
    )

    with open(INDEX_HTML, "w", encoding="utf-8") as f:
        f.write(content)
    print("Patched index.html")

def patch_main_js():
    with open(MAIN_JS, "r", encoding="utf-8") as f:
        content = f.read()

    addon = """
// --- Drag & Drop ---
const dropZone = document.getElementById('dropZone');
const mainContent = document.querySelector('.main-content');

if (mainContent && dropZone) {
    mainContent.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.style.display = 'flex';
    });
    mainContent.addEventListener('dragleave', (e) => {
        // Only hide if we actually leave the container (not its children)
        if (!mainContent.contains(e.relatedTarget)) {
            dropZone.style.display = 'none';
        }
    });
    mainContent.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.style.display = 'none';
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            const file = e.dataTransfer.files[0];
            const formData = new FormData();
            formData.append('file', file);
            
            const isApk = file.name.toLowerCase().endsWith('.apk');
            const url = isApk ? '/api/install' : '/api/push';
            
            if(window.showStatus) window.showStatus(isApk ? 'Đang cài đặt APK...' : 'Đang tải file lên...');
            fetch(url, { method: 'POST', body: formData })
                .then(res => res.json())
                .then(data => {
                    if(window.showStatus) window.showStatus(data.message || (isApk ? 'Cài đặt thành công' : 'Upload thành công'));
                })
                .catch(err => {
                    if(window.showStatus) window.showStatus('Lỗi: ' + err);
                });
        }
    });
}

// --- Keymapping ---
let keymapMode = false;
let keymapNodes = JSON.parse(localStorage.getItem('scrcpy_keymaps') || '[]');
const keymapOverlay = document.getElementById('keymapOverlay');
const hotkeyBtn = document.getElementById('hotkeyConfig');

function renderKeymaps() {
    if (!keymapOverlay) return;
    keymapOverlay.innerHTML = `
       <div style="position:absolute; top: 10px; left: 50%; transform: translateX(-50%); background:rgba(0,0,0,0.8); color:#fbbf24; padding:8px 16px; border-radius:20px; font-family:sans-serif; font-size:0.85rem; font-weight:bold; border:1px solid #fbbf24; box-shadow:0 4px 12px rgba(0,0,0,0.5);">
         <i class="fa-solid fa-pen-ruler"></i> CHẾ ĐỘ GÁN PHÍM: Click vào màn hình để thêm phím. Bấm "Gán phím" lần nữa để lưu.
       </div>
    `;
    keymapNodes.forEach((node, i) => {
        const el = document.createElement('div');
        el.style.position = 'absolute';
        el.style.left = node.x * 100 + '%';
        el.style.top = node.y * 100 + '%';
        el.style.transform = 'translate(-50%, -50%)';
        el.style.width = '30px';
        el.style.height = '30px';
        el.style.borderRadius = '50%';
        el.style.background = 'rgba(236, 72, 153, 0.8)';
        el.style.border = '2px solid #fff';
        el.style.color = '#fff';
        el.style.display = 'flex';
        el.style.alignItems = 'center';
        el.style.justifyContent = 'center';
        el.style.fontWeight = 'bold';
        el.style.fontSize = '12px';
        el.style.zIndex = '95';
        el.innerText = node.key.toUpperCase();
        
        if (keymapMode) {
            el.style.cursor = 'pointer';
            el.onclick = (e) => {
                e.stopPropagation();
                keymapNodes.splice(i, 1);
                renderKeymaps();
            };
        }
        keymapOverlay.appendChild(el);
    });
}

if (hotkeyBtn && keymapOverlay) {
    hotkeyBtn.addEventListener('click', () => {
        keymapMode = !keymapMode;
        if (keymapMode) {
            keymapOverlay.style.display = 'block';
            hotkeyBtn.classList.add('active');
            renderKeymaps();
        } else {
            keymapOverlay.style.display = 'none';
            hotkeyBtn.classList.remove('active');
            localStorage.setItem('scrcpy_keymaps', JSON.stringify(keymapNodes));
        }
    });

    keymapOverlay.addEventListener('click', (e) => {
        if (!keymapMode) return;
        const rect = keymapOverlay.getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width;
        const y = (e.clientY - rect.top) / rect.height;
        
        const key = prompt("Nhập phím (ví dụ: W, A, S, D, Space):");
        if (key && key.trim()) {
            keymapNodes.push({ key: key.trim().toLowerCase(), x, y });
            renderKeymaps();
        }
    });
}

document.addEventListener('keydown', (e) => {
    if (keymapMode) return;
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    
    const node = keymapNodes.find(n => n.key === e.key.toLowerCase());
    if (node) {
        e.preventDefault();
        if (window.socket && window.playerCanvas) {
            const rect = window.playerCanvas.getBoundingClientRect();
            window.socket.emit('touch_event', {
                action: 0, 
                pointer_id: e.keyCode,
                x: node.x * window.playerCanvas.videoWidth,
                y: node.y * window.playerCanvas.videoHeight,
                width: window.playerCanvas.videoWidth,
                height: window.playerCanvas.videoHeight
            });
        }
    }
});

document.addEventListener('keyup', (e) => {
    if (keymapMode) return;
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    
    const node = keymapNodes.find(n => n.key === e.key.toLowerCase());
    if (node) {
        e.preventDefault();
        if (window.socket && window.playerCanvas) {
            const rect = window.playerCanvas.getBoundingClientRect();
            window.socket.emit('touch_event', {
                action: 1, 
                pointer_id: e.keyCode,
                x: node.x * window.playerCanvas.videoWidth,
                y: node.y * window.playerCanvas.videoHeight,
                width: window.playerCanvas.videoWidth,
                height: window.playerCanvas.videoHeight
            });
        }
    }
});
"""
    if "// --- Drag & Drop ---" not in content:
        with open(MAIN_JS, "a", encoding="utf-8") as f:
            f.write("\n" + addon)
        print("Patched main.js")

if __name__ == "__main__":
    patch_index_html()
    patch_main_js()
