package cn.zyh307.conjugaison;

import android.app.Activity;
import android.app.AlertDialog;
import android.graphics.Color;
import android.content.ClipData;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.view.WindowInsets;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.webkit.ValueCallback;
import android.webkit.JavascriptInterface;
import android.widget.FrameLayout;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.File;
import java.io.FileOutputStream;
import android.util.Base64;
import org.json.JSONObject;
import java.util.Collections;

/** Native offline host. All pages and data stay on the device; no network permission. */
public final class MainActivity extends Activity {
    private static final String HOST = "appassets.androidplatform.net";
    private WebView webView;
    private static final int PICK_COVER = 41;
    private static final int SAVE_POSTER = 42;
    private ValueCallback<Uri[]> coverCallback;
    private byte[] pendingPoster;

    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        FrameLayout container = new FrameLayout(this);
        container.setBackgroundColor(Color.rgb(230, 234, 226));
        if (Build.VERSION.SDK_INT >= 30) {
            getWindow().setDecorFitsSystemWindows(false);
            container.setOnApplyWindowInsetsListener(new View.OnApplyWindowInsetsListener() {
                @Override public WindowInsets onApplyWindowInsets(View view, WindowInsets insets) {
                    android.graphics.Insets bars = insets.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout() | WindowInsets.Type.ime());
                    view.setPadding(bars.left, bars.top, bars.right, bars.bottom);
                    return insets;
                }
            });
        }
        webView = new WebView(this);
        webView.setBackgroundColor(Color.rgb(230, 234, 226));
        webView.setOverScrollMode(View.OVER_SCROLL_NEVER);
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(true);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        settings.setJavaScriptCanOpenWindowsAutomatically(false);
        settings.setSupportMultipleWindows(false);
        settings.setTextZoom(100);
        webView.setWebChromeClient(new WebChromeClient() {
            @Override public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback, FileChooserParams params) {
                if (coverCallback != null) coverCallback.onReceiveValue(null);
                coverCallback = callback;
                Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
                intent.addCategory(Intent.CATEGORY_OPENABLE);
                intent.setType("image/*");
                intent.putExtra(Intent.EXTRA_MIME_TYPES, new String[]{"image/jpeg", "image/png", "image/webp", "image/avif"});
                intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                try { startActivityForResult(intent, PICK_COVER); }
                catch (RuntimeException error) { coverCallback.onReceiveValue(null); coverCallback = null; exportResult(false, "无法打开相册，请通过文件管理器选择图片。"); }
                return true;
            }
        });
        webView.addJavascriptInterface(new PosterBridge(), "ConjugaisonNative");
        webView.setWebViewClient(new WebViewClient() {
            @Override public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                return localResponse(request.getUrl());
            }
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                return !"https".equals(uri.getScheme()) || !HOST.equals(uri.getHost());
            }
        });
        container.addView(webView, new FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));
        setContentView(container);
        webView.loadUrl("https://" + HOST + "/index.html");
    }

    private WebResourceResponse localResponse(Uri uri) {
        String path = uri.getPath();
        if (!"https".equals(uri.getScheme()) || !HOST.equals(uri.getHost()) || path == null || path.contains("..") || path.contains("\\")) return notFound();
        if (path.equals("/")) path = "/index.html";
        try {
            InputStream stream = getAssets().open(path.substring(1));
            String mime = "application/octet-stream";
            if (path.endsWith(".html")) mime = "text/html";
            else if (path.endsWith(".js")) mime = "application/javascript";
            else if (path.endsWith(".css")) mime = "text/css";
            else if (path.endsWith(".json")) mime = "application/json";
            else if (path.endsWith(".svg")) mime = "image/svg+xml";
            else if (path.endsWith(".png")) mime = "image/png";
            return new WebResourceResponse(mime, "UTF-8", 200, "OK", Collections.singletonMap("Cache-Control", "no-cache"), stream);
        } catch (IOException error) { return notFound(); }
    }

    private WebResourceResponse notFound() {
        return new WebResourceResponse("text/plain", "UTF-8", 404, "Not Found", Collections.<String, String>emptyMap(), new ByteArrayInputStream(new byte[0]));
    }

    private boolean trustedPage() {
        Uri uri = Uri.parse(webView.getUrl() == null ? "" : webView.getUrl());
        return "https".equals(uri.getScheme()) && HOST.equals(uri.getHost());
    }

    private void exportResult(final boolean success, final String message) {
        runOnUiThread(new Runnable() {
            @Override public void run() {
                if (webView == null || !trustedPage()) return;
                String script = "window.dispatchEvent(new CustomEvent('conjugaison-export',{detail:{success:" + success + ",message:" + JSONObject.quote(message) + "}}))";
                webView.evaluateJavascript(script, null);
            }
        });
    }

    private byte[] decodePoster(String data) {
        if (data == null || !data.startsWith("data:image/png;base64,") || data.length() > 20 * 1024 * 1024) throw new IllegalArgumentException();
        byte[] bytes = Base64.decode(data.substring(data.indexOf(',') + 1), Base64.DEFAULT);
        if (bytes.length < 8 || bytes[0] != (byte) 137 || bytes[1] != 80 || bytes[2] != 78 || bytes[3] != 71) throw new IllegalArgumentException();
        return bytes;
    }

    public final class PosterBridge {
        @JavascriptInterface public void saveImage(final String data) {
            final byte[] bytes;
            try { bytes = decodePoster(data); }
            catch (RuntimeException error) { exportResult(false, "分享图片格式无效，请重新生成。"); return; }
            runOnUiThread(new Runnable() {
                @Override public void run() {
                    if (!trustedPage()) return;
                    if (pendingPoster != null) { exportResult(false, "请先完成上一次保存。"); return; }
                    pendingPoster = bytes;
                    Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT);
                    intent.addCategory(Intent.CATEGORY_OPENABLE);
                    intent.setType("image/png");
                    intent.putExtra(Intent.EXTRA_TITLE, "Conjugaison-" + System.currentTimeMillis() + ".png");
                    try { startActivityForResult(intent, SAVE_POSTER); }
                    catch (RuntimeException error) { pendingPoster = null; exportResult(false, "无法打开保存位置，请尝试分享图片。"); }
                }
            });
        }

        @JavascriptInterface public void shareImage(final String data) {
            final byte[] bytes;
            try {
                bytes = decodePoster(data);
                File directory = new File(getCacheDir(), "share");
                if (!directory.exists() && !directory.mkdirs()) throw new IOException();
                try (FileOutputStream output = new FileOutputStream(new File(directory, "learning-card.png"))) { output.write(bytes); }
            } catch (Exception error) { exportResult(false, "图片生成失败，请重试。"); return; }
            runOnUiThread(new Runnable() {
                @Override public void run() {
                    if (!trustedPage()) return;
                    Uri uri = Uri.parse("content://" + getPackageName() + ".share/learning-card.png");
                    Intent intent = new Intent(Intent.ACTION_SEND);
                    intent.setType("image/png");
                    intent.putExtra(Intent.EXTRA_STREAM, uri);
                    intent.setClipData(ClipData.newUri(getContentResolver(), "法语学习记录", uri));
                    intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                    try { startActivity(Intent.createChooser(intent, "分享学习记录")); exportResult(true, "已打开系统分享。"); }
                    catch (RuntimeException error) { exportResult(false, "没有可用的分享应用，可先保存图片。"); }
                }
            });
        }
    }

    @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == PICK_COVER && coverCallback != null) {
            coverCallback.onReceiveValue(resultCode == RESULT_OK && data != null && data.getData() != null ? new Uri[]{data.getData()} : null);
            coverCallback = null;
        } else if (requestCode == SAVE_POSTER) {
            final byte[] bytes = pendingPoster;
            pendingPoster = null;
            if (resultCode != RESULT_OK || data == null || data.getData() == null) { exportResult(true, "已取消保存。"); return; }
            final Uri target = data.getData();
            new Thread(new Runnable() {
                @Override public void run() {
                    try (OutputStream output = getContentResolver().openOutputStream(target, "wt")) {
                        if (output == null || bytes == null) throw new IOException();
                        output.write(bytes); exportResult(true, "图片已保存到所选位置。");
                    } catch (Exception error) { exportResult(false, "图片保存失败，请重新选择位置。"); }
                }
            }).start();
        }
    }

    @Override public void onBackPressed() {
        if (webView.canGoBack()) webView.goBack();
        else super.onBackPressed();
    }
    @Override protected void onPause() { webView.onPause(); super.onPause(); }
    @Override protected void onResume() { super.onResume(); if (webView != null) webView.onResume(); }
    @Override protected void onDestroy() {
        if (coverCallback != null) { coverCallback.onReceiveValue(null); coverCallback = null; }
        pendingPoster = null;
        if (webView != null) { ((FrameLayout) webView.getParent()).removeView(webView); webView.destroy(); }
        super.onDestroy();
    }
}
