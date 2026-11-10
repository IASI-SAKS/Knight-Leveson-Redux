#!/bin/bash

# for iter in 1 2 3 4 5 6 7 8 9 10
for iter in 1 
do 
    echo "************ Processsing Run ${iter}"
    
    EXPDIR="Experiment-4ImplIndTests"
    RUNDIR="${EXPDIR}/Run${iter}"
        
    PAR_IMPLEMENTATIONS="${EXPDIR}/alternativeImplementations-4ImplIndTests.txt"
    PAR_INDEPENDENT_SUITE="${RUNDIR}/implementationIndependentTestSuite-4ImplIndTests-run${iter}.txt"
    PAR_DEPENDENT_DIR="${RUNDIR}/ImplementationDependentTestSuites-4ImplIndTests-run${iter}"
    PAR_OUTPUTDIR="${RUNDIR}/output";

    mkdir ${PAR_OUTPUTDIR}
    
    python3 coverage_simulator.py --implementations ${PAR_IMPLEMENTATIONS} --independent-suite ${PAR_INDEPENDENT_SUITE} --dependent-dir ${PAR_DEPENDENT_DIR} --output-dir ${PAR_OUTPUTDIR}
    
    TRACESDIR="${PAR_OUTPUTDIR}/traces";

    for FILE in `ls ${TRACESDIR}/*.csv`
    do
        echo "Processsing ${FILE} ..."
        
        TMPNAME=`basename ${FILE} ".csv"`
        TRUE_CROSS_TEST_SUITES_DIR="${PAR_OUTPUTDIR}/tcts/${TMPNAME}"
        mkdir -p ${TRUE_CROSS_TEST_SUITES_DIR}

        TCTS_PAR_IMPLEMENTATIONS="${TRUE_CROSS_TEST_SUITES_DIR}/implementations.txt"
        TCTS_PAR_INDEPENDENT_SUITE="${PAR_INDEPENDENT_SUITE}"
        TCTS_PAR_DEPENDENT_DIR="${TRUE_CROSS_TEST_SUITES_DIR}"

        SOURCENAME=`echo ${TMPNAME} | sed "s/__to__.\+$//"`
        echo ${SOURCENAME} > ${TCTS_PAR_IMPLEMENTATIONS}
        TARGETNAME=`echo ${TMPNAME} | sed "s/^.\+__to__//"`
        echo ${TARGETNAME} >> ${TCTS_PAR_IMPLEMENTATIONS}
# *********************************************
#         echo ${TMPNAME} | sed "s/__to__.\+$//" > ${TCTS_PAR_IMPLEMENTATIONS}
#         echo ${TMPNAME} | sed "s/^.\+__to__//" >> ${TCTS_PAR_IMPLEMENTATIONS}
        sort -u ${TCTS_PAR_IMPLEMENTATIONS} > /tmp/foo
        mv /tmp/foo ${TCTS_PAR_IMPLEMENTATIONS}
        
        python3 extractTrueCrossTests.py ${FILE}
        echo " * extracted from \"${SOURCENAME}\" the TCTS for \"${TARGETNAME}\""
        
        for TCTS_FILE in `find ${TRACESDIR} -name "tcts*"`
        do
            mv ${TCTS_FILE} ${TRUE_CROSS_TEST_SUITES_DIR}
        done
        
        for TCTS_TXT_FILE in `ls ${TRUE_CROSS_TEST_SUITES_DIR}/tcts*.txt`
        do
            TYPE=`basename ${TCTS_TXT_FILE} ".txt" | sed "s/tcts_\([^_]\+\)_.*/\1/"`
            TCTS_PAR_OUTPUTDIR="${TRUE_CROSS_TEST_SUITES_DIR}/output_${TYPE}";
             
            COPYING_DIR=`dirname ${TCTS_TXT_FILE}`
            COPIED_FILE_TARGET="${COPYING_DIR}/${SOURCENAME}.txt"
            echo "copying ${TCTS_TXT_FILE} to ${COPIED_FILE_TARGET}"
            cp ${TCTS_TXT_FILE} ${COPIED_FILE_TARGET}
            DUMMY_FILE_SOURCE="${COPYING_DIR}/${TARGETNAME}.txt"
            echo "creating ${DUMMY_FILE_SOURCE}"
            touch ${DUMMY_FILE_SOURCE}
                                   
            python3 coverage_simulator.py --implementations ${TCTS_PAR_IMPLEMENTATIONS} --independent-suite ${TCTS_PAR_INDEPENDENT_SUITE} --dependent-dir ${TCTS_PAR_DEPENDENT_DIR} --output-dir ${TCTS_PAR_OUTPUTDIR}

            ACTUAL_OUTPUT_DIR="${TCTS_PAR_OUTPUTDIR}/traces"
            ACTUAL_OUTPUT_FILE_CSV="${TMPNAME}.csv"
            ACTUAL_OUTPUT_FILE_JSON="${TMPNAME}.jsonl"
            LINK_ACTUAL_OUTPUT_FILE="result-to-consider"
            cd ${ACTUAL_OUTPUT_DIR}
# ************************************            
# ************************************            
#             LINK_ACTUAL_OUTPUT_FILE_CSV="${LINK_ACTUAL_OUTPUT_FILE}.csv"
#             LINK_ACTUAL_OUTPUT_FILE_JSON="${LINK_ACTUAL_OUTPUT_FILE}.jsonl"
# 
#             ln -fs ${ACTUAL_OUTPUT_FILE_CSV} ${LINK_ACTUAL_OUTPUT_FILE_CSV} 
#             ln -fs ${ACTUAL_OUTPUT_FILE_JSON} ${LINK_ACTUAL_OUTPUT_FILE_JSON}
# ************************************            
            LINK_ACTUAL_OUTPUT_FILE_CSV="${LINK_ACTUAL_OUTPUT_FILE}-csv.lnk"
            LINK_ACTUAL_OUTPUT_FILE_JSON="${LINK_ACTUAL_OUTPUT_FILE}-jsonl.lnk"

            cp ${ACTUAL_OUTPUT_FILE_CSV} ${LINK_ACTUAL_OUTPUT_FILE_CSV} 
            cp ${ACTUAL_OUTPUT_FILE_JSON} ${LINK_ACTUAL_OUTPUT_FILE_JSON}
            rm -rf ./*.csv ./*.jsonl
            ACTUAL_OUTPUT_FILE_CSV="crossExec-${ACTUAL_OUTPUT_FILE_CSV}"
            ACTUAL_OUTPUT_FILE_JSON="crossExec-${ACTUAL_OUTPUT_FILE_JSON}"
            mv ${LINK_ACTUAL_OUTPUT_FILE_CSV} ${ACTUAL_OUTPUT_FILE_CSV} 
            mv ${LINK_ACTUAL_OUTPUT_FILE_JSON} ${ACTUAL_OUTPUT_FILE_JSON}
            rm -rf ../coverage_pairwise*
# ************************************            
# ************************************            
            cd -

            rm -rf ${COPIED_FILE_TARGET}
            rm -rf ${DUMMY_FILE_SOURCE}
        done
        echo " ... done"
    done
exit 1
done
