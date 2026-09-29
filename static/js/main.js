document.addEventListener('DOMContentLoaded', function () {
  const toggle = document.getElementById('navToggle');
  const links = document.getElementById('navLinks');
  if (toggle && links) {
    toggle.addEventListener('click', function () {
      links.classList.toggle('open');
    });
  }

  // Theme auto handled in base.html head script

  const chatToggle = document.getElementById('chatToggle');
  const chatPanel = document.getElementById('chatPanel');
  const chatMessages = document.getElementById('chatMessages');
  const chatInput = document.getElementById('chatInput');
  const chatSend = document.getElementById('chatSend');
  const chatQuick = document.getElementById('chatQuick');

  function appendMsg(text, who) {
    if (!chatMessages) return;
    const div = document.createElement('div');
    div.className = 'chat-msg ' + who;
    div.textContent = text;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function sendChat(msg) {
    msg = (msg || '').trim();
    if (!msg) return;
    appendMsg(msg, 'user');
    if (chatInput) chatInput.value = '';
    var typing = document.createElement('div');
    typing.className = 'chat-msg bot chat-typing';
    typing.textContent = 'Pathari is typing…';
    if (chatMessages) {
      chatMessages.appendChild(typing);
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg })
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (typing.parentNode) typing.parentNode.removeChild(typing);
        var text = data.reply || 'Pathari is thinking…';
        if (data.ai) text = text;
        appendMsg(text, 'bot');
      })
      .catch(function () {
        if (typing.parentNode) typing.parentNode.removeChild(typing);
        appendMsg('Pathari temporarily offline. Check Admin → Settings → AI API key.', 'bot');
      });
  }

  if (chatToggle && chatPanel) {
    chatToggle.addEventListener('click', function () {
      chatPanel.classList.toggle('open');
    });
  }
  if (chatSend) {
    chatSend.addEventListener('click', function () {
      sendChat(chatInput && chatInput.value);
    });
  }
  if (chatInput) {
    chatInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        sendChat(chatInput.value);
      }
    });
  }
  if (chatQuick) {
    chatQuick.querySelectorAll('button').forEach(function (btn) {
      btn.addEventListener('click', function () {
        sendChat(btn.getAttribute('data-msg') || btn.textContent);
      });
    });
  }
});
