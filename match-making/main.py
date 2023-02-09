import csv
import itertools
import json
import logging
import re


def read_data():
    responses = []
    with open("responses.tsv") as file:
        reader = csv.reader(file, delimiter="\t")
        for line in reader:
            responses.append(line)

    with open("schema.json") as file:
        schema = json.load(file)

    # assert that questions match schema
    for data_question, schema_question in zip(responses[0][3:], schema["questions"]):
        assert data_question == schema_question["prompt"], f"\n\t{data_question}\n\t{schema_question['prompt']}"

    # assert that responses match schema
    for total_response in responses[1:]:
        for question_response, schema_question in zip(total_response[3:], schema["questions"]):
            assert question_response == "" or question_response in schema_question["answers"], f"\n\t{question_response}\n\t{schema_question}"


    return schema, responses


def analyize_data(schema, responses):
    email_to_response = {response[1]: response for response in responses[1:]}
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
                    if question_response == "" or question_other_response == "":
                        # Not answering assumes difference of 1
                        difference += 1
                        continue

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
                "similarity": (NUMBER_OF_QUESTIONS - difference) / NUMBER_OF_QUESTIONS * 100
            }

        student_analysis["scores"] = scores
        analysis[email] = student_analysis

    return analysis


def format_analysis(analysis):
    formatted_analysis = []

    for email, student_analysis in analysis.items():
        scores = [(other_email, score) for other_email, score in student_analysis["scores"].items()]
        scores.sort(key=lambda score: score[1]["difference"])
        name = re.search(r"^(.*)@norwood\.k12\.ma\.us$", email).group(1)
        formatted_scores = []
        logging.debug("\t\t" + name)
        for score in scores[:10]:
            # print(f"\t{score[0]:50} difference: {score[1]['difference']:10.3f}\t\tidentical: {score[1]['identical']}")
            other_name = re.search(r"^(.*)@norwood\.k12\.ma\.us$", score[0]).group(1)
            similarity = score[1]['similarity']
            logging.debug(f"\t\t\t{other_name:50} similarity: {similarity:10.2f}%")
            formatted_scores.append((other_name, similarity))

        formatted_analysis.append((name, formatted_scores))
    return formatted_analysis


def batched(iterable, n):
    "Batch data into tuples of length n. The last batch may be shorter."
    # batched('ABCDEFG', 3) --> ABC DEF G
    if n < 1:
        raise ValueError('n must be at least one')
    it = iter(iterable)
    while batch := tuple(itertools.islice(it, n)):
        yield batch


def generate_tex_file(grade, formatted_analysis):
    page_strings = []
    for page in batched(formatted_analysis, 5):
        page_string = ""
        student_strings = []
        for student in page:
            student_string = TEMPLATE
            name = student[0]
            student_string = student_string.replace("XX_NAME", name).replace("XX_GRADE", grade)
            matched_students = student[1]
            for i, other_student in enumerate(matched_students):
                other_name = other_student[0]
                compatibility = f"{other_student[1]:2.2f}"
                student_string = student_string.replace(f"XX_STUDENT_{i + 1}", other_name).replace(f"XX_COMPATIBILITY_{i + 1}", compatibility)
            student_strings.append(student_string)
        page_string = " \\\\\n".join(student_strings)
        page_strings.append(page_string)

    replacement_string = "\n\\newpage\n".join(page_strings)

    with open("template.tex", "r") as template_file:
        template = template_file.read()

    output = template.replace("% REPLACE ME", replacement_string)

    with open(f"{grade}-output.tex", "w") as output_file:
        output_file.write(output)


GRADES = ["9th", "10th", "11th", "12th"]
NUMBER_OF_QUESTIONS = None


TEMPLATE = r"""    \begin{minipage}[b][0.19\textheight][t]{\textwidth}
        \textbf{XX_NAME}

        XX_GRADE Grade

        \bigskip

        \begin{tabularx}{\textwidth}{|| Y | Y || Y | Y ||}
            Student & Compatibility & Student & Compatibility \\
            \hline
            XX_STUDENT_1 & XX_COMPATIBILITY_1\% & XX_STUDENT_6 & XX_COMPATIBILITY_6\% \\
            XX_STUDENT_2 & XX_COMPATIBILITY_2\% & XX_STUDENT_7 & XX_COMPATIBILITY_7\% \\
            XX_STUDENT_3 & XX_COMPATIBILITY_3\% & XX_STUDENT_8 & XX_COMPATIBILITY_8\% \\
            XX_STUDENT_4 & XX_COMPATIBILITY_4\% & XX_STUDENT_9 & XX_COMPATIBILITY_9\% \\
            XX_STUDENT_5 & XX_COMPATIBILITY_5\% & XX_STUDENT_10 & XX_COMPATIBILITY_10\% \\
        \end{tabularx}

    \end{minipage}"""


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    schema, responses = read_data()
    NUMBER_OF_QUESTIONS = len(responses[0][3:])
    for grade in GRADES:
        logging.debug(f"========== {grade} ==========")
        grade_responses = list(filter(lambda response: response[2] == grade, responses))
        analysis = analyize_data(schema, grade_responses)
        formatted_analysis = format_analysis(analysis)
        generate_tex_file(grade, formatted_analysis)
