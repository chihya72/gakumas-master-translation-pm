// Adapted from vertesan/campus (AGPL-3.0); credentials stay in memory.
package config

import "os"

type Config struct {
	AppVersion    string
	MasterVersion string
	RefreshToken  string
	IdToken       string
}

var current = &Config{
	AppVersion:    os.Getenv("CAMPUS_APP_VERSION"),
	MasterVersion: os.Getenv("CAMPUS_MASTER_VERSION"),
	RefreshToken:  os.Getenv("CAMPUS_REFRESH_TOKEN"),
}

func (c *Config) Save()  {}
func GetConfig() *Config { return current }
