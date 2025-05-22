package cli

import (
	"encoding/json"
	"flag"
	"strings"

	"valkey-demo/internal/cobra"
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
	up.Short = "Launch an EC2 demo host"
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
	down.Short = "Terminate a demo host"
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
	list.Short = "Show active runs"
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

	rootFlags, other := splitRootFlags(root, args)
	if err := root.Flags().Parse(rootFlags); err != nil {
		return out, err
	}

	if err := root.Execute(other); err != nil {
		return out, err
	}
	return out, nil
}

func splitRootFlags(cmd *cobra.Command, args []string) ([]string, []string) {
	var rootFlags []string
	var other []string
	fs := cmd.Flags()
	i := 0
	for i < len(args) {
		a := args[i]
		if strings.HasPrefix(a, "-") {
			name := strings.TrimLeft(a, "-")
			if eq := strings.IndexRune(name, '='); eq != -1 {
				name = name[:eq]
			}
			if f := fs.Lookup(name); f != nil {
				rootFlags = append(rootFlags, a)
				if eq := strings.IndexRune(a, '='); eq == -1 && !isBoolFlag(f) {
					if i+1 < len(args) {
						rootFlags = append(rootFlags, args[i+1])
						i++
					}
				}
				i++
				continue
			}
		}
		other = append(other, a)
		i++
	}
	return rootFlags, other
}

func isBoolFlag(f *flag.Flag) bool {
	if bf, ok := f.Value.(interface{ IsBoolFlag() bool }); ok {
		return bf.IsBoolFlag()
	}
	if getter, ok := f.Value.(flag.Getter); ok {
		_, ok := getter.Get().(bool)
		return ok
	}
	return false
}
