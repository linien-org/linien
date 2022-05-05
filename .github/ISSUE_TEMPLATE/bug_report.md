---
name: Bug report
about: Create a report to help us improve
title: ''
labels: bug
assignees: ''

---

Thank you for reporting a bug!

In order to be able to resolve your issue as fast  as possible, please provide us with the version of Linien you are using.

In the case that you are  having trouble with connecting to the linien-server running on the RedPitaya, please try the following first and  include any errors and the console output in your bug report:

First check whether you can ping it by
executing

```bash
ping rp-f0xxxx.local
```

in a command line. If this works, check whether you can connect via SSH:

```bash
ssh rp-f0xxxx.local
```

on the command line. If this is successful, in order to to  check whether the
`linien-server` is running, first confirm that there is a running `screen` session with
the name `linien-server` by  executing `screen -ls`. If that is the case attach it by
running `screen -r linien-server`. If any errors occurred on the server side, they will
be displayed here. Please provide the output in your bug report.
