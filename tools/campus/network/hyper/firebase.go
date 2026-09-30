package hyper

import (
	"bytes"
	"encoding/base64"
	"errors"
	"fmt"
	"github.com/chihya72/gakumas-master-translation-pm/tools/campus/utils/rich"
	"io"
	"net/http"
	"strings"
	"time"

	"github.com/goccy/go-json"
)

const FIREBASE_ENDPOINT = "https://securetoken.googleapis.com/v1/token?key=AIzaSyCe_vKRW5Pc0rTXFksur-ZCDb_kRCxNhng"

// Exchange the game's server-issued Firebase custom token using the official
// signInWithCustomToken flow. Never log request tokens or raw response bodies.
func SignInWithCustomToken(token string) (string, string, error) {
	parts := strings.Split(token, ".")
	if len(parts) != 3 {
		return "", "", errors.New("retry sign-in token is not a Firebase custom JWT")
	}
	claimsBytes, err := base64.RawURLEncoding.DecodeString(parts[1])
	if err != nil {
		return "", "", errors.New("retry sign-in token has invalid JWT claims")
	}
	var claims struct {
		Audience string `json:"aud"`
	}
	if json.Unmarshal(claimsBytes, &claims) != nil || claims.Audience != "https://identitytoolkit.googleapis.com/google.identity.identitytoolkit.v1.IdentityToolkit" {
		return "", "", errors.New("retry sign-in token is not intended for Firebase custom sign-in")
	}
	body, err := json.Marshal(map[string]any{"token": token, "returnSecureToken": true})
	if err != nil {
		return "", "", errors.New("cannot encode Firebase custom sign-in request")
	}
	endpoint := "https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key=AIzaSyCe_vKRW5Pc0rTXFksur-ZCDb_kRCxNhng"
	req, err := http.NewRequest(http.MethodPost, endpoint, bytes.NewReader(body))
	if err != nil {
		return "", "", errors.New("cannot create Firebase custom sign-in request")
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Android-Package", "com.bandainamcoent.idolmaster_gakuen")
	req.Header.Set("X-Android-Cert", "D05C4DC398804FEB2ADF30E8854500D2834EAFED")
	res, err := (&http.Client{Timeout: 20 * time.Second}).Do(req)
	if err != nil {
		return "", "", errors.New("Firebase custom sign-in request failed")
	}
	defer res.Body.Close()
	if res.StatusCode != http.StatusOK {
		return "", "", fmt.Errorf("Firebase custom sign-in returned HTTP %d", res.StatusCode)
	}
	var result struct {
		IDToken      string `json:"idToken"`
		RefreshToken string `json:"refreshToken"`
	}
	if json.NewDecoder(io.LimitReader(res.Body, 1024*1024)).Decode(&result) != nil || result.IDToken == "" || result.RefreshToken == "" {
		return "", "", errors.New("Firebase custom sign-in returned no valid credentials")
	}
	return result.IDToken, result.RefreshToken, nil
}

func GetFirebaseToken(refreshToken string) (string, string) {
	if refreshToken == "" {
		panic(errors.New("refreshToken must be given"))
	}

	headers := &http.Header{
		"Content-Type":        {"application/json"},
		"X-Android-Package":   {"com.bandainamcoent.idolmaster_gakuen"},
		"X-Android-Cert":      {"D05C4DC398804FEB2ADF30E8854500D2834EAFED"},
		"Accept-Language":     {"en-US"},
		"X-Client-Version":    {"Android/Fallback/X22003001/FirebaseCore-Android"},
		"X-Firebase-GMPID":    {"1:544792984478:android:9124c0c2fb92a23780b48f"},
		"X-Firebase-Client":   {"H4sIAAAAAAAAAKtWykhNLCpJSk0sKVayio7VUSpLLSrOzM9TslIyUqoFAFyivEQfAAAA"},
		"X-Firebase-AppCheck": {"eyJlcnJvciI6IlVOS05PV05fRVJST1IifQ=="},
		"User-Agent":          {"Dalvik/2.1.0 (Linux; U; Android 13; Pixel 7 Build/TQ3A.230901.001.C2)"},
		// "Accept-Encoding":     {"gzip"},
	}
	reqBody, err := json.Marshal(map[string]string{
		"grantType":    "refresh_token",
		"refreshToken": refreshToken,
	})
	if err != nil {
		panic(err)
	}
	reqBodyReader := bytes.NewReader(reqBody)
	res, cancel, err := SendRequest(FIREBASE_ENDPOINT, "POST", headers, reqBodyReader, 10, 1)
	if err != nil {
		if cancel != nil {
			cancel()
		}
		panic(err)
	}
	defer res.Body.Close()
	defer cancel()

	buf := &bytes.Buffer{}
	if _, err := io.Copy(buf, res.Body); err != nil {
		panic(err)
	}

	resMap := make(map[string]string)
	if err := json.Unmarshal(buf.Bytes(), &resMap); err != nil {
		panic(err)
	}

	refToken, ok := resMap["refresh_token"]
	if !ok || refToken == "" {
		rich.ErrorThenThrow("refresh_token is absent in firebase response")
	}

	idToken, ok := resMap["id_token"]
	if !ok || idToken == "" {
		rich.ErrorThenThrow("id_token is absent in firebase response")
	}

	return idToken, refToken
}
