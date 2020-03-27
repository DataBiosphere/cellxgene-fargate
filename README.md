# cellxgene-fargate
Host CZI's [cellxgene](https://chanzuckerberg.github.io/cellxgene/) on AWS Fargate.

## Usage

 1) Clone the repository and its submodules:

    ```
    git clone --recurse-submodules git@github.com:DataBiosphere/cellxgene-fargate.git
    ```

 2) Create the `.active` symlink to the active deployment, for example
 
    ```
    (cd deployments && ln -snf sc/dev .active)
    ```
 
 3) Create `deployments/.active/environment.local.py` with any local settings 
    you might need, like `AWS_DEFAULT_PROFILE`. The format of that file is 
    exactly the same as that of `environment.py`. Then run

    ```
    source environment
    ```
    
    Once you've sourced the environment, you can use the `_select` shell 
    function to activate a different deployment, and `_refresh` to source the 
    environment again after changes to any of the `environment*.py` files. 

 4) Create and populate a virtualenv with

    ```   
    make virtualenv
    source .venv/bin/activate
    make envhook  # optional but recommended when using PyCharm
    make requirements.dev
    ```

    The project is configured and all development dependencies have been 
    installed.

 5) To create a Docker image with `cellxgene` inside run

    ```
    make docker_image
    ```

 6) Test the image with 

    ```
    make docker_run
    echo $CELLXGENE_VERSION
    ```
    
    The `cellxgene` version printed by the container should match the value of
    the environment variable.
    
 7) Once per AWS account and region, an Amazon ECR image repository needs to 
    be created:
    
    ```
    make docker_repository
    ```    
 
 8) Push the `cellxgene` Docker image to Amazon ECR with

    ```
    make docker_login
    make docker_push
    ```
 
 9) Provision the AWS resources needed to run `cellxgene` as a Fargate container 
    in Amazon ECS behind an EC2 application load balancer:
    
    ```
    _preauth  # if you're assuming an IAM role requiring MFA
    make terraform 
    ```
