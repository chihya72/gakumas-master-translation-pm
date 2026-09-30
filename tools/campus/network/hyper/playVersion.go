package hyper

import (
	"errors"
	"fmt"
	"net/http"
	"regexp"
	"strings"
	"time"

	"github.com/PuerkitoBio/goquery"
)

const GAME_ID = "com.bandainamcoent.idolmaster_gakuen"

func GetPlayVersion() (string, error) {
	url := fmt.Sprintf("https://play.google.com/store/apps/details?id=%s", GAME_ID)
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return "", err
	}
	header := http.Header{
		"User-Agent": {"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0"},
	}
	req.Header = header
	res, err := (&http.Client{Timeout: 20 * time.Second}).Do(req)
	if err != nil {
		return "", err
	}
	defer res.Body.Close()
	if res.StatusCode != 200 {
		return "", fmt.Errorf("Google Play returned HTTP %d", res.StatusCode)
	}
	doc, err := goquery.NewDocumentFromReader(res.Body)
	if err != nil {
		return "", err
	}
	var version string
	doc.Find("script").EachWithBreak(func(i int, s *goquery.Selection) bool {
		scriptContent := strings.TrimSpace(s.Text())
		if strings.Contains(scriptContent, "key: 'ds:5'") {
			reg := regexp.MustCompile(`\[\[\["([\d\.]+)"\]\],\[\[\[\d+\]\]\,\[\[\[\d+,"`)
			match := reg.FindStringSubmatch(scriptContent)
			if len(match) == 2 {
				version = match[1]
				return false
			}
		}
		return true
	})
	if version == "" {
		return "", errors.New("Cannot find ds:5 in <script>, perhaps GooglePlay has got their DOM of webpage changed.")
	}
	return version, nil
}
