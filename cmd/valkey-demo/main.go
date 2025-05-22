package main

import (
	"fmt"
	"os"

	"valkey-demo/internal/cli"
)

func main() {
	out, err := cli.Execute(os.Args[1:])
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	if out != "" {
		fmt.Println(out)
	}
}
