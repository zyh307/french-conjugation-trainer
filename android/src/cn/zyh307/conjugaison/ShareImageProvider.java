package cn.zyh307.conjugaison;

import android.content.ContentProvider;
import android.content.ContentValues;
import android.database.Cursor;
import android.database.MatrixCursor;
import android.net.Uri;
import android.os.ParcelFileDescriptor;
import android.provider.OpenableColumns;
import java.io.File;
import java.io.FileNotFoundException;

/** Grants a chosen receiving app read-only access to the generated poster. */
public final class ShareImageProvider extends ContentProvider {
    @Override public boolean onCreate() { return true; }
    private File image(Uri uri) throws FileNotFoundException {
        if (!"/learning-card.png".equals(uri.getPath())) throw new FileNotFoundException();
        File file = new File(getContext().getCacheDir(), "share/learning-card.png");
        if (!file.isFile()) throw new FileNotFoundException();
        return file;
    }
    @Override public String getType(Uri uri) { return "image/png"; }
    @Override public ParcelFileDescriptor openFile(Uri uri, String mode) throws FileNotFoundException {
        if (!"r".equals(mode)) throw new FileNotFoundException("Read only");
        return ParcelFileDescriptor.open(image(uri), ParcelFileDescriptor.MODE_READ_ONLY);
    }
    @Override public Cursor query(Uri uri, String[] projection, String selection, String[] selectionArgs, String sortOrder) {
        String[] columns = projection == null ? new String[]{OpenableColumns.DISPLAY_NAME, OpenableColumns.SIZE} : projection;
        MatrixCursor cursor = new MatrixCursor(columns);
        try {
            File file = image(uri); Object[] row = new Object[columns.length];
            for (int i = 0; i < columns.length; i++) { if (OpenableColumns.DISPLAY_NAME.equals(columns[i])) row[i] = "Conjugaison.png"; else if (OpenableColumns.SIZE.equals(columns[i])) row[i] = file.length(); }
            cursor.addRow(row);
        } catch (FileNotFoundException ignored) { }
        return cursor;
    }
    @Override public Uri insert(Uri uri, ContentValues values) { throw new UnsupportedOperationException(); }
    @Override public int delete(Uri uri, String selection, String[] args) { throw new UnsupportedOperationException(); }
    @Override public int update(Uri uri, ContentValues values, String selection, String[] args) { throw new UnsupportedOperationException(); }
}
