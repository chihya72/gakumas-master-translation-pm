module github.com/chihya72/gakumas-master-translation-pm/tools/campus

go 1.25.0

require (
	github.com/PuerkitoBio/goquery v1.10.0
	github.com/fatih/color v1.18.0
	github.com/goccy/go-json v0.10.4
	github.com/goccy/go-yaml v1.15.11
	github.com/golang-jwt/jwt/v5 v5.2.2
	github.com/mutecomm/go-sqlcipher/v4 v4.4.2
	golang.org/x/sync v0.19.0
	google.golang.org/grpc v1.79.3
	google.golang.org/protobuf v1.36.10
)

require (
	github.com/andybalholm/cascadia v1.3.2 // indirect
	github.com/mattn/go-colorable v0.1.13 // indirect
	github.com/mattn/go-isatty v0.0.20 // indirect
	github.com/stretchr/testify v1.9.0 // indirect
	golang.org/x/net v0.48.0 // indirect
	golang.org/x/sys v0.39.0 // indirect
	golang.org/x/text v0.32.0 // indirect
	google.golang.org/genproto/googleapis/rpc v0.0.0-20251202230838-ff82c1b0f217 // indirect
)

// Generated game protobuf types and table mapping.
require vertesan/campus v0.0.0

replace vertesan/campus => github.com/vertesan/campus v0.0.0-20260802081808-a7f5b047b475
