# cellxgene-fargate
Host CZI's [cellxgene](https://chanzuckerberg.github.io/cellxgene/) on AWS Fargate.

## Usage

 1) Clone the repository and its submodules:

   ```
   git clone --recurse-submodules git@github.com:DataBiosphere/cellxgene-fargate.git
   ```

 2) Create `environment.local` with any local settings you might need, like 
    `AWS_PROFILE`. Then run

    ```
    source environment
    ``` 

 3) Create and populate a virtualenv with

    ```   
    make virtualenv
    source .venv/bin/activate
    make requirements.dev
    ```

    The project is configured and all development dependencies have been 
    installed.

 4) To create a Docker image with `cellxgene` inside run

    ```
    make docker_image
    ```

 5) Test the image with 

    ```
    make docker_run
    ```
    
    The `cellxgene` help text should be printed.
    
 6) Once per AWS account and region, an Amazon ECR image repository needs to 
    be created:
    
    ```
    make docker_repository
    ```    
 
 7) Push the `cellxgene` Docker image to Amazon ECR with

    ```
    make docker_login
    make docker_push
    ```
 
 8) Provision the AWS resources needed to run `cellxgene` as a Fargate container 
    in Amazon ECS behind an EC2 application load balancer:
    
    ```
    _preauth  # if you're assuming an IAM role that requires MFA
    make terraform 
    ```
