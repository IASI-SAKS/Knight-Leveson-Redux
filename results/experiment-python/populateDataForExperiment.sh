#!/bin/bash

POSITIONAL_ARGS=()
if [ $# -eq 0 ]
then
      echo "Some partameters are mandaroty"
      echo "Run: $0 --help"
      exit 1
fi

# while [[ $# -gt 0 ]]; do
#   case $1 in
#     -z|--zero)
#       MAGIC_NUMBER="0"
#       shift # past argument
#       ;;
#     -t|--two)
#       MAGIC_NUMBER="2"
#       shift # past argument
#       ;;
#     -T|--TWO)
# #       MAGIC_NUMBER="2High"
#       MAGIC_NUMBER="2Low"
#       shift # past argument
#       ;;
#     -f|--four)
#       MAGIC_NUMBER="4"
#       shift # past argument
#       ;;
#     -F|--FOUR)
# #       MAGIC_NUMBER="4VeryHigh"
# #       MAGIC_NUMBER="4High"
#       MAGIC_NUMBER="4Low"
#       shift # past argument
#       ;;
#     -v|--five)
#       MAGIC_NUMBER="5"
#       shift # past argument
#       ;;
#     -V|--FIVE)
# #       MAGIC_NUMBER="5VeryHigh"
# #       MAGIC_NUMBER="5High"
#       MAGIC_NUMBER="5Low"
#       shift # past argument
#       ;;
#     -s|--six)
#       MAGIC_NUMBER="6"
#       shift # past argument
#       ;;
#     -S|--SIX)
# #       MAGIC_NUMBER="6VeryHigh"
# #       MAGIC_NUMBER="6High"
#       MAGIC_NUMBER="6Low"
#       shift # past argument
#       ;;
#     -e|--eight)
#       MAGIC_NUMBER="8"
#       shift # past argument
#       ;;
#     -E|--EIGHT)
# #       MAGIC_NUMBER="8VeryHigh"
# #       MAGIC_NUMBER="8High"
#       MAGIC_NUMBER="8Low"
#       shift # past argument
#       ;;
#     -x|--ten)
#       MAGIC_NUMBER="10"
#       shift # past argument
#       ;;
#     -X|--TEN)
# #       MAGIC_NUMBER="10VeryHigh"
# #       MAGIC_NUMBER="10High"
#       MAGIC_NUMBER="10Low"
#       shift # past argument
#       ;;
#     -xx|--twenty)
#       MAGIC_NUMBER="20"
#       shift # past argument
#       ;;
#     -XX|--TWENTY)
# #       MAGIC_NUMBER="20VeryHigh"
# #       MAGIC_NUMBER="20High"
#       MAGIC_NUMBER="20Low"
#       shift # past argument
#       ;;
#     -h|--help)
#       echo "$0 <[-z|--zero]|[-t|--two]|[-T|--TWO]|[-f|--four]|[-F|--FOUR]|[-v|--five]|[-V|--FIVE]|[-s|--six]|[-S|--SIX]|[-e|--eight]|[-E|--EIGHT]|[-x|--ten]|[-X|--TEN]|[-xx|--twenty]|[-XX|--TWENTY]> [-h|--help]"
#       exit 1
#       ;;
#     -*|--*)
#       echo "Unknown option $1"
#       echo "Run: $0 --help"
#       exit 1
#       ;;
#     *)
#       POSITIONAL_ARGS+=("$1") # save positional arg
#       shift # past argument
#       ;;
#   esac
# done
MAGIC_NUMBER="4"
MAGIC_SUFFIX=""

while [[ $# -gt 0 ]]; do
  case $1 in
    -n|--magic-number)
      MAGIC_NUMBER="$2"
      shift # past option
      shift # past argument
      ;;
    -s|--suffix)
      MAGIC_SUFFIX="$2"
      shift # past option
      shift # past argument
      ;;
    -h|--help)
      echo "$0 [-n|--magic-number <n>] [-s|--suffix <str>] [-h|--help]"
      exit 1
      ;;
    -*|--*)
      echo "Unknown option $1"
      echo "Run: $0 --help"
      exit 1
      ;;
    *)
      POSITIONAL_ARGS+=("$1") # save positional arg
      shift # past argument
      ;;
  esac
done

MAGIC_LABEL="${MAGIC_NUMBER}${MAGIC_SUFFIX}"

for iter in 1 2 3 4 5 6 7 8 9 10
# for iter in 2 3 4 5 6 7 8 9 10
# for iter in 1 
# for iter in 2 
# for iter in 3 4 5
# for iter in 6 7 8 9 10
do 
    echo "************ Processsing Run ${iter}"
    
    EXPDIR="Experiment-${MAGIC_LABEL}ImplIndTests"
    RUNDIR="${EXPDIR}/Run${iter}"
        
    PAR_IMPLEMENTATIONS="${EXPDIR}/alternativeImplementations-${MAGIC_LABEL}ImplIndTests.txt"
    PAR_INDEPENDENT_SUITE="${RUNDIR}/implementationIndependentTestSuite-${MAGIC_LABEL}ImplIndTests-run${iter}.txt"
    PAR_DEPENDENT_DIR="${RUNDIR}/ImplementationDependentTestSuites-${MAGIC_LABEL}ImplIndTests-run${iter}"
    PAR_OUTPUTDIR="${RUNDIR}/output";

echo "Configuration:"
echo "  * $EXPDIR"
echo "  * $RUNDIR"
echo "  * $PAR_IMPLEMENTATIONS"
echo "  * $PAR_INDEPENDENT_SUITE"
echo "  * $PAR_DEPENDENT_DIR"
echo "  * $PAR_OUTPUTDIR"


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
done
