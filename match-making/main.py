import csv
import json

data = []
with open("data.tsv") as file:
    reader = csv.reader(file, delimiter="\t")
    for line in reader:
        data.append(line)

with open("schema.json") as file:
    schema = json.load(file)

# assert that questions match schema
for data_question, schema_question in zip(data[0][3:], schema["questions"]):
    assert data_question == schema_question["prompt"], f"\n\t{data_question}\n\t{schema_question['prompt']}"

# assert that responses match schema
for total_response in data[1:]:
    for question_response, schema_question in zip(total_response[3:], schema["questions"]):
        assert question_response in schema_question["answers"], f"\n\t{question_response}\n\t{schema_question}"

email_to_response = {response[1]: response for response in data[1:]}

analysis = {}

# for each student
for email, response in email_to_response.items():
    student_analysis = {
        "response": response,
    }
    scores = {}
    # compare to each other student
    for other_email, other_response in email_to_response.items():
        if email == other_email:
            # don't compare student to themselves
            continue

        # golf scoring
        difference = 0
        # number of identical responses
        identical = 0
        # compare students response to other response with schema
        for question_response, question_other_response, schema_question in zip(
            response[3:], other_response[3:], schema["questions"]
        ):
            if question_response == question_other_response:
                # do nothing if answers are the same
                identical += 1
                continue

            if schema_question["type"] == "distinct":
                difference += 1
                continue

            if schema_question["type"] == "ranked":
                answers = schema_question["answers"]
                index = answers.index(question_response)
                other_index = answers.index(question_other_response)
                difference += abs((other_index - index) / (len(answers) - 1))
                continue

            raise RuntimeError

        scores[other_email] = {
            # "response": other_response,
            "difference": difference,
            "identical": identical,
        }

    student_analysis["scores"] = scores
    analysis[email] = student_analysis

for email, student_analysis in analysis.items():
    scores = [(other_email, score) for other_email, score in student_analysis["scores"].items()]
    scores.sort(key=lambda score: score[1]["difference"])
    print(email)
    for score in scores[:3]:
        print(f"\t{score[0]:50} difference: {score[1]['difference']:10.3f}\t\tidentical: {score[1]['identical']}")
