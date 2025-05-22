package cobra

import (
	"flag"
	"fmt"
)

type Command struct {
	Use   string
	Short string
	RunE  func(cmd *Command, args []string) error

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

func (c *Command) AddCommand(cmds ...*Command) {
	for _, cmd := range cmds {
		if c.subCommands == nil {
			c.subCommands = make(map[string]*Command)
		}
		c.subCommands[cmd.Use] = cmd
	}
}

func (c *Command) Execute(args []string) error {
	if len(args) == 0 {
		if c.RunE != nil {
			c.Flags().Parse(args)
			return c.RunE(c, c.Flags().Args())
		}
		return nil
	}
	if sub, ok := c.subCommands[args[0]]; ok {
		sub.Flags().Parse(args[1:])
		if sub.RunE != nil {
			return sub.RunE(sub, sub.Flags().Args())
		}
		return nil
	}
	c.Flags().Parse(args)
	if c.RunE != nil {
		return c.RunE(c, c.Flags().Args())
	}
	return fmt.Errorf("unknown command: %s", args[0])
}
