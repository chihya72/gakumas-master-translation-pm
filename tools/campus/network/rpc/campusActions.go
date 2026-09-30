package rpc

import (
	"fmt"
	"github.com/chihya72/gakumas-master-translation-pm/tools/campus/config"
	"github.com/chihya72/gakumas-master-translation-pm/tools/campus/network/hyper"
	"github.com/chihya72/gakumas-master-translation-pm/tools/campus/utils/rich"
	"google.golang.org/grpc"
	"google.golang.org/grpc/metadata"
	"sort"
	papi "vertesan/campus/proto/papi"
)

func (c *CampusClient) systemFirstCheck() {
	client := papi.NewSystemClient(c.conn)
	ctx, cancel := c.prepareContext()
	defer (*cancel)()
	req := &papi.SystemCheckRequest{}
	rich.Info("Calling SystemFirstCheck...")
	resp, err := client.Check(*ctx, req)
	if err != nil {
		panic(err)
	}
	rich.Info("SystemFirstCheck: integrity enabled=%t, maintenance=%t", resp.GetPlayIntegrityEnabled(), resp.GetMaintenanceInfo().GetInMaintenance())
}

func (c *CampusClient) systemCheck() {
	client := papi.NewSystemClient(c.conn)
	ctx, cancel := c.prepareContext()
	defer (*cancel)()
	req := &papi.SystemCheckRequest{
		IdToken: c.idToken,
	}
	rich.Info("Calling SystemCheck...")
	resp, err := client.Check(*ctx, req)
	if err != nil {
		panic(err)
	}
	rich.Info("SystemCheck: integrity enabled=%t, maintenance=%t", resp.GetPlayIntegrityEnabled(), resp.GetMaintenanceInfo().GetInMaintenance())
}

func (c *CampusClient) authLogin() {
	client := papi.NewAuthClient(c.conn)
	ctx, cancel := c.prepareContext()
	defer (*cancel)()
	req := &papi.AuthLoginRequest{
		IdToken: c.idToken,
	}
	rich.Info("Calling AuthLogin...")
	var header, trailer metadata.MD
	resp, err := client.Login(*ctx, req, grpc.Header(&header), grpc.Trailer(&trailer))
	if err != nil {
		panic(err)
	}
	if resp.GameAuthToken == "" && resp.GetRetrySignInToken() != "" {
		rich.Info("Auth.Login requested Firebase custom sign-in.")
		idToken, refreshToken, err := hyper.SignInWithCustomToken(resp.GetRetrySignInToken())
		if err != nil {
			panic(err)
		}
		c.idToken = idToken
		cfg := config.GetConfig()
		cfg.IdToken, cfg.RefreshToken = idToken, refreshToken
		req.IdToken = idToken
		// Retry exactly once after the server-authorized Firebase exchange.
		retryCtx, retryCancel := c.prepareContext()
		defer (*retryCancel)()
		resp, err = client.Login(*retryCtx, req, grpc.Header(&header), grpc.Trailer(&trailer))
		if err != nil {
			panic(err)
		}
	}
	if resp.GameAuthToken != "" {
		c.authToken = resp.GameAuthToken
		c.headers["x-auth-token"] = c.authToken
	} else {
		keys := make([]string, 0, len(header)+len(trailer))
		for key := range header {
			keys = append(keys, key)
		}
		for key := range trailer {
			keys = append(keys, key)
		}
		sort.Strings(keys)
		// Report state and metadata names only; response and metadata values can contain credentials.
		rich.ErrorThenThrow("Auth.Login returned no game token (retry token present=%t, terms=%d, consents=%d, unknown bytes=%d, metadata keys=%s)", resp.GetRetrySignInToken() != "", len(resp.GetTerms()), len(resp.GetConsents()), len(resp.ProtoReflect().GetUnknown()), fmt.Sprint(keys))
	}
}

func (c *CampusClient) masterGet() {
	client := papi.NewMasterClient(c.conn)
	ctx, cancel := c.prepareContext()
	defer (*cancel)()
	req := &papi.Empty{}
	rich.Info("Calling MasterGet...")
	resp, err := client.Get(*ctx, req)
	if err != nil {
		panic(err)
	}
	if resp.GetMasterTag().GetVersion() != "" {
		c.masterVersion = resp.MasterTag.Version
		c.headers["x-master-version"] = c.masterVersion
		c.MasterResp = resp
	} else {
		rich.ErrorThenThrow("Get a nil MasterTag.Version from server while get masterdb.")
	}
}
