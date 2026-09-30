// Adapted from vertesan/campus, licensed under AGPL-3.0.
package master

import (
	"bytes"
	"database/sql"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"strings"

	"github.com/chihya72/gakumas-master-translation-pm/tools/campus/network/hyper/downloader"
	_ "github.com/mutecomm/go-sqlcipher/v4"
	"google.golang.org/protobuf/proto"
	"vertesan/campus/proto/papi"
)

const MASTER_RAW_PATH = "cache/masterRaw"
const MASTER_YAML_PATH = "cache/masterYaml"

func DownloadAndDecrypt(response *papi.MasterGetResponse) {
	header := &http.Header{
		"User-Agent":      {"UnityPlayer/6000.0.77f1 (UnityWebRequest/1.0, libcurl/8.10.1-DEV)"},
		"Accept":          {"*/*"},
		"X-Unity-Version": {"6000.0.77f1"},
	}
	entries := []*downloader.Entry{}
	for _, pack := range response.MasterTag.MasterTagPacks {
		if filepath.Base(pack.Type) != pack.Type || strings.ContainsAny(pack.Type, "/\\\\") {
			panic("invalid master table name")
		}
		entries = append(entries, &downloader.Entry{Url: pack.DownloadUrl, SaveFileName: pack.Type})
	}
	worker := downloader.NewDownloader(30, header, MASTER_RAW_PATH, 5)
	worker.SetEntries(entries)
	if err := worker.DownloadAll(); err != nil {
		panic(err)
	}
	if err := os.MkdirAll(MASTER_YAML_PATH, 0755); err != nil {
		panic(err)
	}
	for _, pack := range response.MasterTag.MasterTagPacks {
		decryptTable(pack)
	}
}

func decryptTable(pack *papi.MasterGetResponse_MasterTagPack) {
	name := fmt.Sprintf("%s?_pragma_key=x'%s'", filepath.Join(MASTER_RAW_PATH, pack.Type), pack.CryptoKey)
	db, err := sql.Open("sqlite3", name)
	if err != nil {
		panic(err)
	}
	defer db.Close()
	rows, err := db.Query(fmt.Sprintf("select data from \"%s\";", strings.ReplaceAll(pack.Type, "\"", "\"\"")))
	if err != nil {
		panic(err)
	}
	defer rows.Close()
	var output bytes.Buffer
	for rows.Next() {
		var data []byte
		if err := rows.Scan(&data); err != nil {
			panic(err)
		}
		message := newTableMessage(pack.Type)
		if err := proto.Unmarshal(data, message); err != nil {
			panic(err)
		}
		if err := checkKnownFields(message.ProtoReflect()); err != nil {
			panic(err)
		}
		yamlBytes, err := YamlMarshal(message)
		if err != nil {
			panic(err)
		}
		lines := bytes.Split(bytes.TrimSuffix(yamlBytes, []byte("\n")), []byte("\n"))
		output.WriteString("- ")
		output.Write(lines[0])
		output.WriteByte('\n')
		for _, line := range lines[1:] {
			output.WriteString("  ")
			output.Write(line)
			output.WriteByte('\n')
		}
	}
	if err := rows.Err(); err != nil {
		panic(err)
	}
	if err := os.WriteFile(filepath.Join(MASTER_YAML_PATH, pack.Type+".yaml"), output.Bytes(), 0644); err != nil {
		panic(err)
	}
}
