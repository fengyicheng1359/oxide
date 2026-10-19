// 保留普通页面的 .html 地址，同时让目录首页继续使用末尾的 /。
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;

    if (path.endsWith('/index.html')) {
      url.pathname = path.slice(0, -'index.html'.length);
      return Response.redirect(url, 301);
    }

    if (path.endsWith('/')) {
      url.pathname = path + 'index.html';
      return env.ASSETS.fetch(new Request(url, request));
    }

    const assetResponse = await env.ASSETS.fetch(request);
    if (assetResponse.status !== 404 || (request.method !== 'GET' && request.method !== 'HEAD') || path.endsWith('.html')) {
      return assetResponse;
    }

    // 旧的无后缀地址可能已被搜索引擎收录，只在目标文件存在时跳回 .html。
    const directoryUrl = new URL(url);
    directoryUrl.pathname = path + '/index.html';
    if ((await env.ASSETS.fetch(new Request(directoryUrl, { method: 'HEAD' }))).ok) {
      url.pathname = path + '/';
      return Response.redirect(url, 301);
    }

    const pageUrl = new URL(url);
    pageUrl.pathname = path + '.html';
    if ((await env.ASSETS.fetch(new Request(pageUrl, { method: 'HEAD' }))).ok) {
      return Response.redirect(pageUrl, 301);
    }

    return assetResponse;
  },
};
