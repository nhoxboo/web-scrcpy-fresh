document.addEventListener('DOMContentLoaded', () => {
    // Dropdown toggle logic
    const moreBtn = document.getElementById('moreToolsBtn');
    const moreMenu = document.getElementById('moreToolsMenu');

    if (moreBtn && moreMenu) {
        moreBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            moreMenu.classList.toggle('show');
            moreBtn.classList.toggle('active');
        });

        document.addEventListener('click', (e) => {
            if (!moreMenu.contains(e.target) && e.target !== moreBtn) {
                moreMenu.classList.remove('show');
                moreBtn.classList.remove('active');
            }
        });

        const dropdownItems = moreMenu.querySelectorAll('.dropdown-item');
        dropdownItems.forEach(item => {
            item.addEventListener('click', () => {
                moreMenu.classList.remove('show');
                moreBtn.classList.remove('active');
            });
        });
    }

    // Add default transport mode if not set
    if (!localStorage.getItem('transportMode')) {
        localStorage.setItem('transportMode', 'webrtc');
    }
});

// Add nice visual effects
document.addEventListener('DOMContentLoaded', () => {
    // Buttons hover ripple effect
    const buttons = document.querySelectorAll('.btn, .tool');
    buttons.forEach(btn => {
        btn.addEventListener('mousedown', function(e) {
            let rect = this.getBoundingClientRect();
            let x = e.clientX - rect.left;
            let y = e.clientY - rect.top;
            let ripples = document.createElement('span');
            ripples.style.left = x + 'px';
            ripples.style.top = y + 'px';
            ripples.classList.add('ripple');
            this.appendChild(ripples);
            setTimeout(() => {
                ripples.remove();
            }, 1000);
        });
    });
});

window.initMacros = function() {
      const recBtn = document.getElementById('macroRec');
      const stopBtn = document.getElementById('macroStop');
      const playBtn = document.getElementById('macroPlay');
      const clearBtn = document.getElementById('macroClear');
      const hotkeyBtn = document.getElementById('hotkeyConfig');
      const gameBtn = document.getElementById('window.gameMode');

      recBtn.onclick = ()=>{
        window.macroEvents = [];
        window.isRecordingMacro = true;
        window.macroStartAt = Date.now();
        recBtn.classList.add('active');
        localStorage.setItem(MACRO_KEY, JSON.stringify(window.macroEvents));
        window.st('Bắt đầu ghi macro...');
      };
      stopBtn.onclick = ()=>{
        window.isRecordingMacro = false;
        recBtn.classList.remove('active');
        localStorage.setItem(MACRO_KEY, JSON.stringify(window.macroEvents));
        window.st(`Đã dừng ghi macro (${window.macroEvents.length} bước)`);
      };
      clearBtn.onclick = ()=>{
        window.macroEvents = [];
        localStorage.setItem(MACRO_KEY, '[]');
        window.st('Đã xóa macro');
      };
      playBtn.onclick = async ()=>{
        const events = Array.isArray(window.macroEvents) ? [...window.macroEvents] : [];
        if(!events.length){ window.st('Chưa có macro để chạy'); return; }
        window.isRecordingMacro = false;
        recBtn.classList.remove('active');
        window.isPlayingMacro = true;
        window.st(`Đang chạy macro (${events.length} bước)...`);
        const startAt = Date.now();
        for(const ev of events){
          const wait = Math.max(0, ev.t - (Date.now() - startAt));
          if(wait) await new Promise(r=>setTimeout(r, wait));
          if(ev.type==='power') window.doPower();
          if(ev.type==='keyTap') window.keyTap(ev.code, ev.actionName || 'key');
          if(ev.type==='control' && ev.payload){ window.socket.emit('control_data', ev.payload); }
        }
        window.isPlayingMacro = false;
        window.st('Chạy macro xong');
      };

      const syncGameButton = ()=>{
        gameBtn.classList.toggle('active', window.gameMode);
        gameBtn.title = `Game mode: ${window.gameMode ? 'ON' : 'OFF'}`;
      };
      syncGameButton();
      gameBtn.onclick = ()=>{
        window.gameMode = !window.gameMode;
        localStorage.setItem(GAME_MODE_KEY, window.gameMode ? '1' : '0');
        if(!window.gameMode){
          // Release held movement keys when turning game mode off
          [19,20,21,22].forEach(code=>window.keyUp(code));
          window.heldKeys.clear();
        }
        syncGameButton();
        window.st(`Game mode: ${window.gameMode ? 'ON' : 'OFF'}`);
      };

      hotkeyBtn.onclick = ()=>{
        const tips = `Gán phím (code KeyboardEvent):\n`+
          `Power (${window.hotkeys.power})\nVol- (${window.hotkeys.voldown})\nVol+ (${window.hotkeys.volup})\nBack (${window.hotkeys.back})\nHome (${window.hotkeys.home})\nRecent (${window.hotkeys.recent})\nPlay Macro (${window.hotkeys.macroPlay})\n\nNhập JSON mới hoặc Cancel để bỏ qua.`;
        const raw = prompt(tips, JSON.stringify(hotkeys, null, 2));
        if(!raw) return;
        try{
          const next = JSON.parse(raw);
          hotkeys = {...hotkeys, ...next};
          localStorage.setItem(HOTKEY_KEY, JSON.stringify(hotkeys));
          window.st('Đã lưu gán phím');
        }catch{
          window.st('JSON không hợp lệ, chưa lưu');
        }
      };

      window.addEventListener('keydown', (e)=>{
        if(['INPUT','TEXTAREA'].includes((e.target?.tagName||'').toUpperCase())) return;

        const holdMap = {
          [window.hotkeys.moveUp]: 19,    // DPAD_UP
          [window.hotkeys.moveDown]: 20,  // DPAD_DOWN
          [window.hotkeys.moveLeft]: 21,  // DPAD_LEFT
          [window.hotkeys.moveRight]: 22, // DPAD_RIGHT
        };
        const tapMap = {
          [window.hotkeys.power]: ()=>{ if(window.isRecordingMacro) window.macroEvents.push({ t: Date.now()-window.macroStartAt, type:'power', actionName:'power' }); window.doPower(); },
          [window.hotkeys.voldown]: doVolDown,
          [window.hotkeys.volup]: doVolUp,
          [window.hotkeys.back]: doBack,
          [window.hotkeys.home]: doHome,
          [window.hotkeys.recent]: doRecent,
          [window.hotkeys.macroPlay]: ()=>playBtn.click(),
          [window.hotkeys.jump]: ()=>window.keyTap(62, 'jump'),
          [window.hotkeys.skill1]: ()=>window.keyTap(29, 'skill1'), // A
          [window.hotkeys.skill2]: ()=>window.keyTap(30, 'skill2'), // B
          [window.hotkeys.skill3]: ()=>window.keyTap(31, 'skill3'), // C
        };

        if(window.gameMode && holdMap[e.code]){
          e.preventDefault();
          if(window.heldKeys.has(e.code)) return;
          window.heldKeys.add(e.code);
          window.keyDown(holdMap[e.code]);
          return;
        }

        const fn = tapMap[e.code];
        if(fn){ e.preventDefault(); fn(); }
      });

      window.addEventListener('keyup', (e)=>{
        if(!window.gameMode) return;
        const holdMap = {
          [window.hotkeys.moveUp]: 19,
          [window.hotkeys.moveDown]: 20,
          [window.hotkeys.moveLeft]: 21,
          [window.hotkeys.moveRight]: 22,
        };
        if(holdMap[e.code]){
          e.preventDefault();
          window.heldKeys.delete(e.code);
          window.keyUp(holdMap[e.code]);
        }
      });


};
