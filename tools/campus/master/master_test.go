package master

import (
	"database/sql"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"vertesan/campus/proto/papi"
)

func TestUnknownMasterTableRows(t *testing.T) {
	for _, test := range []struct {
		name string
		rows [][]byte
	}{
		{name: "empty table"},
		{name: "nonempty table", rows: [][]byte{{0x0a, 0x03, 'n', 'e', 'w'}}},
		{name: "empty blob is still a row", rows: [][]byte{{}}},
	} {
		t.Run(test.name, func(t *testing.T) {
			t.Chdir(t.TempDir())
			for _, path := range []string{MASTER_RAW_PATH, MASTER_YAML_PATH} {
				if err := os.MkdirAll(path, 0755); err != nil {
					t.Fatal(err)
				}
			}
			pack := &papi.MasterGetResponse_MasterTagPack{
				Type:      "FutureMasterTable",
				CryptoKey: strings.Repeat("01", 32),
			}
			if HasTable(pack.Type) {
				t.Fatal("test requires a table absent from the client schema")
			}
			name := fmt.Sprintf("%s?_pragma_key=x'%s'", filepath.Join(MASTER_RAW_PATH, pack.Type), pack.CryptoKey)
			db, err := sql.Open("sqlite3", name)
			if err != nil {
				t.Fatal(err)
			}
			t.Cleanup(func() { db.Close() })
			if _, err := db.Exec(`CREATE TABLE "FutureMasterTable" (data BLOB)`); err != nil {
				t.Fatal(err)
			}
			for _, row := range test.rows {
				if _, err := db.Exec(`INSERT INTO "FutureMasterTable" (data) VALUES (?)`, row); err != nil {
					t.Fatal(err)
				}
			}
			if err := db.Close(); err != nil {
				t.Fatal(err)
			}
			var failure any
			func() {
				defer func() { failure = recover() }()
				decryptTable(pack)
			}()
			yamlPath := filepath.Join(MASTER_YAML_PATH, pack.Type+".yaml")
			if len(test.rows) > 0 {
				want := "unsupported master table FutureMasterTable: update client schema"
				if fmt.Sprint(failure) != want {
					t.Fatalf("unknown row must fail schema decoding: got %v", failure)
				}
				if _, err := os.Stat(yamlPath); !errors.Is(err, os.ErrNotExist) {
					t.Fatalf("unknown rows must not produce YAML: %v", err)
				}
				return
			}
			if failure != nil {
				t.Fatalf("empty table does not require a row schema: %v", failure)
			}
			data, err := os.ReadFile(yamlPath)
			if err != nil {
				t.Fatal(err)
			}
			if len(data) != 0 {
				t.Fatalf("empty table should export the existing empty YAML format: %q", data)
			}
		})
	}
}
