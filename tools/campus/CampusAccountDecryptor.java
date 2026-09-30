// Read-only Firebase Auth storage helper. No game code is loaded or modified.
import java.io.File;
import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.security.KeyStore;
import java.util.Arrays;
import java.util.Base64;
import javax.crypto.Cipher;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import javax.xml.parsers.DocumentBuilderFactory;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;

public final class CampusAccountDecryptor {
    private static final String PACKAGE = "com.bandainamcoent.idolmaster_gakuen";
    private static final String EXPECTED_PERSISTENCE_KEY =
        "W0RFRkFVTFRd+MTo1NDQ3OTI5ODQ0Nzg6YW5kcm9pZDo5MTI0YzBjMmZiOTJhMjM3ODBiNDhm";

    private static long varint(byte[] data, int[] position) {
        long value = 0;
        for (int shift = 0; shift < 64; shift += 7) {
            if (position[0] >= data.length) throw new IllegalArgumentException("Truncated protobuf");
            int next = data[position[0]++] & 255;
            value |= (long)(next & 127) << shift;
            if (next < 128) return value;
        }
        throw new IllegalArgumentException("Invalid protobuf integer");
    }

    private static byte[] field(byte[] data, int wanted, int occurrence) {
        int[] position = {0};
        int found = 0;
        while (position[0] < data.length) {
            long tag = varint(data, position);
            int number = (int)(tag >>> 3), wire = (int)(tag & 7);
            if (wire == 0) { varint(data, position); continue; }
            if (wire != 2) throw new IllegalArgumentException("Unsupported protobuf field");
            long size = varint(data, position);
            if (size < 0 || size > data.length - position[0]) throw new IllegalArgumentException("Invalid protobuf length");
            int start = position[0];
            position[0] += (int)size;
            if (number == wanted && found++ == occurrence) return Arrays.copyOfRange(data, start, position[0]);
        }
        throw new IllegalArgumentException("Missing protobuf field");
    }

    private static long integer(byte[] data, int wanted) {
        int[] position = {0};
        while (position[0] < data.length) {
            long tag = varint(data, position);
            int number = (int)(tag >>> 3), wire = (int)(tag & 7);
            if (wire == 0) {
                long value = varint(data, position);
                if (number == wanted) return value;
            } else if (wire == 2) {
                long size = varint(data, position);
                if (size < 0 || size > data.length - position[0]) throw new IllegalArgumentException("Invalid protobuf length");
                position[0] += (int)size;
            } else { throw new IllegalArgumentException("Unsupported protobuf field"); }
        }
        throw new IllegalArgumentException("Missing protobuf integer");
    }

    private static String preference(File file, String wanted) throws Exception {
        if (!file.isFile() || file.length() > 1048576) throw new IllegalArgumentException("Invalid preference file");
        byte[] contents = Files.readAllBytes(file.toPath());
        String xml = new String(contents, StandardCharsets.UTF_8).toUpperCase(java.util.Locale.ROOT);
        if (xml.contains("<!DOCTYPE") || xml.contains("<!ENTITY")) throw new IllegalArgumentException("XML declarations not supported");
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        factory.setExpandEntityReferences(false);
        NodeList values = factory.newDocumentBuilder().parse(new ByteArrayInputStream(contents)).getDocumentElement().getElementsByTagName("string");
        for (int i = 0; i < values.getLength(); i++) {
            Element value = (Element)values.item(i);
            if (wanted.equals(value.getAttribute("name"))) return value.getTextContent();
        }
        throw new IllegalArgumentException("Preference not found");
    }

    private static byte[] hex(String text) {
        if ((text.length() & 1) != 0) throw new IllegalArgumentException("Invalid hex");
        byte[] data = new byte[text.length() / 2];
        for (int i = 0; i < data.length; i++) {
            int high = Character.digit(text.charAt(i * 2), 16);
            int low = Character.digit(text.charAt(i * 2 + 1), 16);
            if (high < 0 || low < 0) throw new IllegalArgumentException("Invalid hex");
            data[i] = (byte)(high * 16 + low);
        }
        return data;
    }

    private static byte[] decrypt(SecretKey key, byte[] ciphertext) throws Exception {
        if (ciphertext.length < 28) throw new IllegalArgumentException("Invalid GCM ciphertext");
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.DECRYPT_MODE, key, new GCMParameterSpec(128, Arrays.copyOfRange(ciphertext, 0, 12)));
        return cipher.doFinal(ciphertext, 12, ciphertext.length - 12);
    }

    private static String jsonString(String json, String name) throws Exception {
        Class<?> objectType = Class.forName("org.json.JSONObject");
        Object object = objectType.getConstructor(String.class).newInstance(json);
        return (String)objectType.getMethod("getString", String.class).invoke(object, name);
    }

    private static void selfTest() throws Exception {
        byte[] key = new byte[32];
        SecretKeySpec aes = new SecretKeySpec(key, "AES");
        byte[] nonce = new byte[12];
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.ENCRYPT_MODE, aes, new GCMParameterSpec(128, nonce));
        byte[] fake = "synthetic-account-test".getBytes(StandardCharsets.UTF_8);
        byte[] encrypted = cipher.doFinal(fake);
        byte[] combined = new byte[12 + encrypted.length];
        System.arraycopy(encrypted, 0, combined, 12, encrypted.length);
        if (!Arrays.equals(fake, decrypt(aes, combined))) throw new IllegalStateException("GCM check failed");
        byte[] proto = {8, 7, 18, 3, 1, 2, 3};
        if (integer(proto, 1) != 7 || !Arrays.equals(field(proto, 2, 0), new byte[]{1, 2, 3})) {
            throw new IllegalStateException("Protobuf check failed");
        }
        System.out.println("AES-GCM and keyset parser checks passed; only synthetic data used.");
    }

    public static void main(String[] arguments) {
        String stage = "arguments";
        try {
            if (arguments.length == 1 && "--self-test".equals(arguments[0])) { selfTest(); return; }
            if (arguments.length != 2 || !EXPECTED_PERSISTENCE_KEY.equals(arguments[1])) {
                throw new IllegalArgumentException("Invalid helper arguments");
            }
            int uid = Integer.parseInt(arguments[0]);
            if (uid < 10000 || uid > 99999) throw new IllegalArgumentException("Invalid game uid");
            stage = "application_identity";
            Class<?> os = Class.forName("android.system.Os");
            os.getMethod("setgid", int.class).invoke(null, uid);
            os.getMethod("setuid", int.class).invoke(null, uid);
            stage = "encrypted_keyset_file";
            File folder = new File("/data/data/" + PACKAGE + "/shared_prefs");
            byte[] encryptedSet = hex(preference(new File(folder,
                "com.google.firebase.auth.api.crypto." + arguments[1] + ".xml"), "StorageCryptoKeyset"));
            stage = "keystore_provider";
            // app_process does not run ActivityThread's normal provider setup.
            Class<?> provider;
            try { provider = Class.forName("android.security.keystore2.AndroidKeyStoreProvider"); }
            catch (ClassNotFoundException missing) { provider = Class.forName("android.security.keystore.AndroidKeyStoreProvider"); }
            provider.getMethod("install").invoke(null);
            KeyStore store = KeyStore.getInstance("AndroidKeyStore");
            store.load(null);
            stage = "keystore_key_access";
            SecretKey master = (SecretKey)store.getKey("firebear_main_key_id_for_storage_crypto." + arguments[1], null);
            if (master == null) throw new IllegalStateException("Keystore key unavailable");
            stage = "keyset_decryption";
            byte[] keyset = decrypt(master, field(encryptedSet, 2, 0));
            long primary = integer(keyset, 1);
            byte[] selected = null;
            for (int i = 0; i < 32; i++) {
                byte[] candidate = field(keyset, 2, i);
                if (integer(candidate, 3) == primary && integer(candidate, 2) == 1) { selected = candidate; break; }
            }
            if (selected == null) throw new IllegalStateException("Primary key unavailable");
            byte[] keyData = field(selected, 1, 0);
            if (!"type.googleapis.com/google.crypto.tink.AesGcmKey".equals(new String(field(keyData, 1, 0), StandardCharsets.UTF_8))) {
                throw new IllegalArgumentException("Unsupported key type");
            }
            byte[] rawKey = field(field(keyData, 2, 0), 3, 0);
            if (rawKey.length != 32) throw new IllegalArgumentException("Unsupported AES key length");
            stage = "auth_state_file";
            String saved = preference(new File(folder,
                "com.google.firebase.auth.api.Store." + arguments[1] + ".xml"), "com.google.firebase.auth.FIREBASE_USER");
            if (!saved.startsWith("ENCRYPTED:")) throw new IllegalArgumentException("Expected encrypted auth state");
            byte[] encryptedUser = Base64.getDecoder().decode(saved.substring(10));
            long prefixType = integer(selected, 4);
            if (prefixType == 1) {
                if (encryptedUser.length < 5 || encryptedUser[0] != 1) throw new IllegalArgumentException("Invalid Tink prefix");
                long id = 0;
                for (int i = 1; i < 5; i++) id = (id << 8) | (encryptedUser[i] & 255);
                if (id != primary) throw new IllegalArgumentException("Tink key id mismatch");
                encryptedUser = Arrays.copyOfRange(encryptedUser, 5, encryptedUser.length);
            } else if (prefixType != 3) { throw new IllegalArgumentException("Unsupported Tink prefix"); }
            stage = "auth_state_decryption";
            byte[] user = decrypt(new SecretKeySpec(rawKey, "AES"), encryptedUser);
            Arrays.fill(rawKey, (byte)0);
            Arrays.fill(keyset, (byte)0);
            stage = "token_extraction";
            String state = jsonString(new String(user, StandardCharsets.UTF_8), "cachedTokenState");
            String token = jsonString(state, "refresh_token");
            Arrays.fill(user, (byte)0);
            if (token.isEmpty()) throw new IllegalArgumentException("Empty refresh token");
            // Parent Python captures this pipe in memory; never run the helper in a displayed terminal.
            System.out.print("CAMPUS_TOKEN:" + token);
        } catch (Throwable failure) {
            System.out.print("CAMPUS_ERROR:" + stage + "/" + failure.getClass().getSimpleName());
            System.exit(1);
        }
    }
}
