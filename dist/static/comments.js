/* 同一语种共享留言板；此脚本只渲染入口，点击前不请求 Disqus 资源。 */
(() => {
  const script = document.querySelector('script[data-community-script]');
  if (!script || document.querySelector('.community')) return;
  const messages = {
    zh: { title: '在岛上活下来，你有什么独门妙招？', intro: '分享生存经验、聊聊游戏趣事，也可以向其他玩家提问。', button: '看看大家怎么说 / 我也说两句', policy: '评论政策', loading: '正在加载评论…', error: '评论暂时无法加载，请检查网络或内容拦截设置后重试。', retry: '重试加载', name: '中文' },
    en: { title: 'What’s your secret to surviving the island?', intro: 'Share your tips, swap island stories, or ask fellow survivors a question.', button: 'Join the conversation', policy: 'Comment policy', loading: 'Loading comments…', error: 'Comments could not load. Check your connection or content blocker and try again.', retry: 'Try again', name: 'English' },
    ja: { title: '島で生き抜く、あなたの秘訣は？', intro: '生き残るコツや島での体験を語り合ったり、仲間に質問したりしましょう。', button: 'コメントを見る・投稿する', policy: 'コメントポリシー', loading: 'コメントを読み込み中…', error: '読み込めませんでした。接続やコンテンツブロック設定を確認して再試行してください。', retry: '再試行', name: '日本語' },
    ko: { title: '섬에서 살아남는 나만의 비결이 있나요?', intro: '생존 팁과 섬에서의 재미있는 경험을 나누거나 다른 플레이어에게 질문하세요.', button: '댓글 보기 / 작성', policy: '댓글 정책', loading: '댓글을 불러오는 중…', error: '댓글을 불러올 수 없습니다. 연결이나 콘텐츠 차단 설정을 확인하고 다시 시도하세요.', retry: '다시 시도', name: '한국어' },
    fr: { title: 'Quel est votre secret pour survivre sur l’île ?', intro: 'Partagez vos astuces, racontez vos aventures sur l’île ou posez une question aux autres survivants.', button: 'Voir / ajouter un commentaire', policy: 'Règles des commentaires', loading: 'Chargement des commentaires…', error: 'Chargement impossible. Vérifiez votre connexion ou votre bloqueur de contenu et réessayez.', retry: 'Réessayer', name: 'Français' },
    de: { title: 'Was ist dein Geheimnis fürs Überleben auf der Insel?', intro: 'Teile deine Tipps, erzähle von deinen Abenteuern auf der Insel oder frage andere Überlebende.', button: 'Kommentare lesen / schreiben', policy: 'Kommentarregeln', loading: 'Kommentare werden geladen…', error: 'Laden fehlgeschlagen. Prüfe deine Verbindung oder deinen Inhaltsblocker und versuche es erneut.', retry: 'Erneut versuchen', name: 'Deutsch' },
    es: { title: '¿Cuál es tu secreto para sobrevivir en la isla?', intro: 'Comparte tus consejos, cuenta tus aventuras en la isla o pregunta a otros supervivientes.', button: 'Ver / añadir comentarios', policy: 'Normas de comentarios', loading: 'Cargando comentarios…', error: 'No se pudieron cargar los comentarios. Revisa tu conexión o bloqueador de contenido e inténtalo de nuevo.', retry: 'Reintentar', name: 'Español' },
    pt: { title: 'Qual é o seu segredo para sobreviver na ilha?', intro: 'Compartilhe suas dicas, conte suas aventuras na ilha ou faça uma pergunta a outros sobreviventes.', button: 'Ver / adicionar comentários', policy: 'Regras dos comentários', loading: 'Carregando comentários…', error: 'Não foi possível carregar os comentários. Verifique sua conexão ou bloqueador de conteúdo e tente novamente.', retry: 'Tentar novamente', name: 'Português' },
    ru: { title: 'В чём ваш секрет выживания на острове?', intro: 'Делитесь советами, рассказывайте истории с острова или задавайте вопросы другим выжившим.', button: 'Читать / добавить комментарий', policy: 'Правила комментариев', loading: 'Загрузка комментариев…', error: 'Не удалось загрузить комментарии. Проверьте подключение или блокировщик контента и повторите попытку.', retry: 'Повторить', name: 'Русский' }
  };
  const language = document.documentElement.dataset.language || 'en';
  const text = messages[language];
  if (!text) return;
  const section = document.createElement('section');
  section.className = 'community';
  section.setAttribute('aria-labelledby', 'community-title');
  section.innerHTML = '<div class="community-invite"><div class="community-copy"><h2 id="community-title"></h2><p></p><a class="community-policy"></a></div><button class="community-button" type="button" aria-controls="disqus_thread" aria-expanded="false"></button></div><p class="community-status" role="status" hidden></p><div id="disqus_thread" class="community-thread" hidden></div>';
  section.querySelector('h2').textContent = text.title;
  section.querySelector('.community-copy p').textContent = text.intro;
  const policy = section.querySelector('.community-policy');
  policy.textContent = text.policy;
  policy.href = new URL('../' + language + '/comment-policy.html', script.src).href;
  const button = section.querySelector('button');
  button.textContent = text.button;
  const status = section.querySelector('.community-status');
  const thread = section.querySelector('#disqus_thread');
  document.body.append(section);
  let state = 'idle';
  let timeout;
  let embed;
  const fail = () => {
    if (state !== 'loading') return;
    state = 'failed';
    clearTimeout(timeout);
    button.disabled = false;
    button.textContent = text.retry;
    status.hidden = false;
    status.textContent = text.error;
  };
  const ready = () => {
    clearTimeout(timeout);
    state = 'ready';
    status.hidden = true;
    button.disabled = false;
    button.textContent = text.button;
  };
  button.addEventListener('click', () => {
    if (state === 'loading') return;
    if (state === 'ready') {
      thread.scrollIntoView({ behavior: 'auto', block: 'start' });
      return;
    }
    state = 'loading';
    button.disabled = true;
    button.textContent = text.loading;
    button.setAttribute('aria-expanded', 'true');
    thread.hidden = false;
    status.hidden = false;
    status.textContent = text.loading;
    // 使用固定语种标识及首页 URL，不受当前页面、查询参数或锚点影响。
    window.disqus_config = function () {
      this.page.url = script.dataset.siteUrl + '/' + language + '/index.html';
      this.page.identifier = language + '/community';
      this.page.title = 'MyOxide Community — ' + text.name;
      this.language = language;
      this.callbacks.onReady = [ready];
    };
    timeout = setTimeout(fail, 20000);
    // 超时后已有 Disqus 实例时复用它，避免重复嵌入；网络失败则重新加载脚本。
    if (window.DISQUS) {
      window.DISQUS.reset({ reload: true, config: window.disqus_config });
      return;
    }
    if (embed) embed.remove();
    embed = document.createElement('script');
    embed.src = 'https://' + script.dataset.shortname + '.disqus.com/embed.js';
    embed.async = true;
    embed.onerror = fail;
    document.head.append(embed);
  });
})();
