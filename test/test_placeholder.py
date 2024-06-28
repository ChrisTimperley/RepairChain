from pathlib import Path
from repairchain.models.project import Project
from repairchain.strategies.llms.simple_yolo import SimpleYolo
from repairchain.models.diagnosis import Diagnosis

def test_true() -> None:
    assert True

def test_llm_output_parsing() -> None:
    # The provided patches output (example)
    output = """
BEGIN BUG FIX
1
BEGIN MODIFIED FILENAME
mock_vp.c
END MODIFIED FILENAME
BEGIN MODIFIED FUNCTION NAME
func_a
END MODIFIED FUNCTION NAME
BEGIN MODIFIED CODE
void func_a(){
    char* buff;
    int i = 0;
    do{
        printf("input item:");
        buff = &items[i][0];
        i++;
        fgets(buff, sizeof(items[0]), stdin);
        buff[strcspn(buff, "\\n")] = 0;
    }while(strlen(buff)!=0 && i < 3);
    i--;
}
END MODIFIED CODE
BEGIN DESCRIPTION
Restricting the `fgets` function call to the proper size of the target buffer (`sizeof(items[0])`) prevents potential buffer overflow. Additionally, checking the index `i` during the loop ensures it does not exceed the limit, preventing out-of-bounds access.
END DESCRIPTION
END BUG FIX

BEGIN BUG FIX
2
BEGIN MODIFIED FILENAME
mock_vp.c
END MODIFIED FILENAME
BEGIN MODIFIED FUNCTION NAME
func_a
END MODIFIED FUNCTION NAME
BEGIN MODIFIED CODE
void func_a(){
    char* buff;
    int i = 0;
    do{
        printf("input item:");
        buff = &items[i][0];
        fgets(buff, sizeof(items[0]), stdin);
        buff[strcspn(buff, "\\n")] = 0;
        i++;
    }while(strlen(buff)!=0 && i < 3);
    if(i < 3) i--;
}
END MODIFIED CODE
BEGIN DESCRIPTION
The `fgets` function is now limited to the size of the buffer. The check `i < 3` ensures that the index does not exceed the array bounds. Post-loop adjustment to `i` is conditional based on the iteration limit.
END DESCRIPTION
END BUG FIX
    """

    patches = SimpleYolo.extract_patches(output)

    expected_patches = [
        (
            "mock_vp.c",
            "func_a",
            """void func_a(){
    char* buff;
    int i = 0;
    do{
        printf("input item:");
        buff = &items[i][0];
        i++;
        fgets(buff, sizeof(items[0]), stdin);
        buff[strcspn(buff, "\\n")] = 0;
    }while(strlen(buff)!=0 && i < 3);
    i--;
}"""
        ),
        (
            "mock_vp.c",
            "func_a",
            """void func_a(){
    char* buff;
    int i = 0;
    do{
        printf("input item:");
        buff = &items[i][0];
        fgets(buff, sizeof(items[0]), stdin);
        buff[strcspn(buff, "\\n")] = 0;
        i++;
    }while(strlen(buff)!=0 && i < 3);
    if(i < 3) i--;
}"""
        ),
    ]

    assert patches == expected_patches, f"Expected {expected_patches}, but got {patches}"


def test_simple_yolo_mock() -> None:
    model = "oai-gpt-4o"
    litellm_url = "http://0.0.0.0:4000"

    project_path = "litellm/project.json"
    # Load the project
    with Project.load(project_path) as project:
        # Create the Diagnosis object
        diagnosis = Diagnosis(
            project=project,
            bug_type=None,  # Provide appropriate BugType instance
            implicated_functions=[]  # Provide list of implicated functions
        )

    # simple_yolo = SimpleYolo.build(diagnosis, model, litellm_url)
    # print(simple_yolo.prompt)
    # output = simple_yolo.call_llm(simple_yolo.prompt, simple_yolo.model, simple_yolo.litellm_url)
    # print(output)
    # diffs = simple_yolo.create_diff_from_patches(output)
    # for d in diffs:
    #     print(d)
    #assert False
    assert True

