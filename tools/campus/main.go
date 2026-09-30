// Master-data-only adaptation of vertesan/campus, licensed under AGPL-3.0.
package main

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/chihya72/gakumas-master-translation-pm/tools/campus/config"
	"github.com/chihya72/gakumas-master-translation-pm/tools/campus/master"
	"github.com/chihya72/gakumas-master-translation-pm/tools/campus/network/hyper"
	"github.com/chihya72/gakumas-master-translation-pm/tools/campus/network/rpc"
)

func main() {
	cfg := config.GetConfig()
	if cfg.RefreshToken == "" {
		panic("CAMPUS_REFRESH_TOKEN is required")
	}
	version, err := hyper.GetPlayVersion()
	if err != nil {
		if cfg.AppVersion == "" {
			panic(err)
		}
		version = cfg.AppVersion
	}
	cfg.AppVersion = version
	fmt.Printf("Game app version: %s\n", version)
	cfg.IdToken, cfg.RefreshToken = hyper.GetFirebaseToken(cfg.RefreshToken)
	client := rpc.NewCampusClient(cfg.IdToken, cfg.AppVersion)
	client.DoLogin()
	tag := client.MasterResp.GetMasterTag()
	if tag == nil || tag.Version == "" || len(tag.MasterTagPacks) == 0 {
		panic("master response is empty")
	}
	fmt.Printf("Local master version: %s; server: %s\n", cfg.MasterVersion, tag.Version)
	if cfg.MasterVersion == tag.Version {
		return
	}
	for _, pack := range tag.MasterTagPacks {
		if !master.HasTable(pack.Type) {
			panic(fmt.Sprintf("unsupported master table %s: update client schema", pack.Type))
		}
	}
	if err := os.MkdirAll("cache", 0755); err != nil {
		panic(err)
	}
	master.DownloadAndDecrypt(client.MasterResp)
	if err := os.WriteFile(filepath.Join("cache", "master_version"), []byte(tag.Version+"\n"), 0644); err != nil {
		panic(err)
	}
}
