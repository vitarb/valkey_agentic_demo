package cli

import (
	"encoding/json"
	"github.com/spf13/cobra"
)

type Options struct {
	Region  string `json:"region,omitempty"`
	Profile string `json:"profile,omitempty"`
	DryRun  bool   `json:"dry_run,omitempty"`
}

func newRoot(opts *Options, out *string) *cobra.Command {
	cmd := cobra.NewCommand("valkey-demo")

	cmd.Flags().StringVar(&opts.Region, "region", "", "AWS region")
	cmd.Flags().StringVar(&opts.Profile, "profile", "", "AWS profile")
	cmd.Flags().BoolVar(&opts.DryRun, "dry-run", false, "dry run")

	// up command
	var instanceType, runID string
	var spot, ssm bool
	up := cobra.NewCommand("up")
	up.Flags().StringVar(&instanceType, "instance-type", "", "instance type")
	up.Flags().BoolVar(&spot, "spot", false, "spot")
	up.Flags().BoolVar(&ssm, "ssm", false, "ssm")
	up.Flags().StringVar(&runID, "run-id", "", "run id")
	up.RunE = func(cmd *cobra.Command, args []string) error {
		payload := map[string]interface{}{
			"action":        "up",
			"region":        opts.Region,
			"profile":       opts.Profile,
			"dry_run":       opts.DryRun,
			"instance_type": instanceType,
			"spot":          spot,
			"ssm":           ssm,
			"run_id":        runID,
		}
		b, err := json.Marshal(payload)
		if err != nil {
			return err
		}
		*out = string(b)
		return nil
	}

	// down command
	down := cobra.NewCommand("down")
	down.RunE = func(cmd *cobra.Command, args []string) error {
		payload := map[string]interface{}{
			"action":  "down",
			"region":  opts.Region,
			"profile": opts.Profile,
			"dry_run": opts.DryRun,
		}
		b, err := json.Marshal(payload)
		if err != nil {
			return err
		}
		*out = string(b)
		return nil
	}

	// list command
	list := cobra.NewCommand("list")
	list.RunE = func(cmd *cobra.Command, args []string) error {
		payload := map[string]interface{}{
			"action":  "list",
			"region":  opts.Region,
			"profile": opts.Profile,
			"dry_run": opts.DryRun,
		}
		b, err := json.Marshal(payload)
		if err != nil {
			return err
		}
		*out = string(b)
		return nil
	}

	cmd.AddCommand(up, down, list)
	return cmd
}

// Execute parses args and returns JSON payload string
func Execute(args []string) (string, error) {
	opts := &Options{}
	var out string
	root := newRoot(opts, &out)

	// Parse global flags first; FlagSet stops parsing at the first non-flag
	root.Flags().Parse(args)
	remaining := root.Flags().Args()

	if err := root.Execute(remaining); err != nil {
		return out, err
	}
	return out, nil
}
