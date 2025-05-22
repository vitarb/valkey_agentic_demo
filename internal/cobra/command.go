package cobra // import "github.com/spf13/cobra"

import (
	"flag"
	"fmt"
)

type Command struct {
	Use   string
	Short string
	Long  string

	RunE func(cmd *Command, args []string) error

	flagSet     *flag.FlagSet
	subCommands map[string]*Command
}

func NewCommand(use string) *Command {
	return &Command{
		Use:         use,
		flagSet:     flag.NewFlagSet(use, flag.ContinueOnError),
		subCommands: make(map[string]*Command),
	}
}

func (c *Command) Flags() *flag.FlagSet {
	if c.flagSet == nil {
		c.flagSet = flag.NewFlagSet(c.Use, flag.ContinueOnError)
	}
	return c.flagSet
}

func (c *Command) PersistentFlags() *flag.FlagSet {
	return c.Flags()
}

func (c *Command) AddCommand(cmds ...*Command) {
	for _, cmd := range cmds {
		if c.subCommands == nil {
			c.subCommands = make(map[string]*Command)
		}
		c.subCommands[cmd.Use] = cmd
	}
}

func (c *Command) Execute(args []string) error {
	for _, a := range args {
		if a == "-h" || a == "--help" {
			fmt.Printf("%s - %s\n", c.Use, c.Short)
			if c.Long != "" {
				fmt.Println(c.Long)
			}
			if len(c.subCommands) > 0 {
				fmt.Println("Commands:")
				for _, sc := range c.subCommands {
					fmt.Printf("  %s\t%s\n", sc.Use, sc.Short)
				}
			}
			return nil
		}
	}
	if !c.Flags().Parsed() {
		if err := c.Flags().Parse(args); err != nil {
			return err
		}
		args = c.Flags().Args()
	}
	if len(args) == 0 {
		if c.RunE != nil {
			return c.RunE(c, []string{})
		}
		return nil
	}
	if sub, ok := c.subCommands[args[0]]; ok {
		return sub.Execute(args[1:])
	}
	if c.RunE != nil {
		return c.RunE(c, args)
	}
	return fmt.Errorf("unknown command: %s", args[0])
}
