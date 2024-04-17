## Template jobs

### Test `chat`
```bash
naptha run chat --prompt "tell me a joke"
```

### Test `hello_world`
1. Have the appropriate yaml files
```bash
naptha run hello_world -f ./example_yamls/hello_world_daimon_template.yml
```

### Test `generate_image`

Executing a job
```bash
naptha run generate_image -f ./example_yamls/sd_daimon_template.yml
```

Reading output from the above job using the job_id
```bash
naptha read_storage -id jgj9r4zve1wdg3kouoq2 -o .
```

### Test `image_to_image`
Write a file to storage
```bash
naptha write_storage -i output.png
```

Use the folder id and update it in a yaml and run the job
```bash
naptha run image_to_image -f ./example_yamls/sdi2i_daimon_template.yml
```

Get the output
```bash
naptha read_storage -id vv6n1t6us5nsfrgfd7u2 -o .
```

## Docker jobs

### Test `docker_hello_world`
```bash
naptha run docker_hello_world -f ./example_yamls/docker_hello_world.yml
```

### Test `docker_cv2_image`
```bash
naptha run docker_cv2_image -f ./example_yamls/docker_cv2_image.yml
```

Get the output
```bash
naptha read_storage -id lyqye155cs6agtuwx9zi -o .
```

